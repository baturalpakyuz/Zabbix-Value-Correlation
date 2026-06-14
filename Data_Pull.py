import requests
import psycopg
import uuid
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


class ZabbixDataExporter:

    def __init__(
        self,
        api_config,
        db_config,
        api_token,
        start_time,
        end_time,
        output_folder,
        logger=None,
        progress_callback=None
    ):
        self.api_config = api_config
        self.db_config = db_config
        self.api_token = api_token
        self.start_time = start_time
        self.end_time = end_time
        self.output_folder = output_folder

        # optional hooks (for UI integration)
        self.logger = logger
        self.progress_callback = progress_callback

    # =========================
    # UTIL
    # =========================
    def log(self, msg):
        if self.logger:
            self.logger(msg)
        else:
            print(msg)

    def progress(self, current, total):
        if self.progress_callback:
            self.progress_callback(current, total)

    # =========================
    # API
    # =========================
    def get_unique_hosts(self):

        headers = {
            "Content-Type": "application/json-rpc",
            "Authorization": f"Bearer {self.api_token}"
        }

        payload = {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {"output": ["hostid"]},
            "id": str(uuid.uuid4())
        }

        try:
            response = requests.post(
                self.api_config["url"],
                json=payload,
                headers=headers,
                timeout=20
            )

            response.raise_for_status()
            data = response.json()

            hosts = [h["hostid"] for h in data.get("result", [])]

            self.log(f"Fetched {len(hosts)} hosts from API")
            return hosts

        except Exception as e:
            self.log(f"[API ERROR] {e}")
            return []

    # =========================
    # DB
    # =========================
    def db_call(self, host_id):

        query = """
        SELECT 
            i.name,
            his.value,
            his.clock,
            it.tag
        FROM history his
        JOIN items i ON his.itemid = i.itemid
        JOIN hosts h ON i.hostid = h.hostid
        JOIN item_tag it ON it.itemid = i.itemid
        WHERE i.type IN (5, 3, 0)
          AND h.hostid = %s
          AND his.clock BETWEEN %s AND %s
        """

        try:
            with psycopg.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (host_id, self.start_time, self.end_time))
                    rows = cur.fetchall()

            if not rows:
                return None

            df = pd.DataFrame(rows, columns=["name", "value", "clock", "tag"])
            df["hostid"] = host_id

            return df

        except Exception as e:
            self.log(f"[DB ERROR] host {host_id}: {e}")
            return None

    # =========================
    # PARQUET
    # =========================
    def write_parquet(self, df):

        if df is None or df.empty:
            return

        try:
            table = pa.Table.from_pandas(df)

            pq.write_to_dataset(
                table,
                root_path=self.output_folder,
                partition_cols=["tag"],
                compression="snappy"
            )

        except Exception as e:
            self.log(f"[PARQUET ERROR] {e}")

    # =========================
    # PIPELINE
    # =========================
    def export_all_hosts(self):

        hosts = self.get_unique_hosts()

        if not hosts:
            self.log("No hosts found. Exiting.")
            return

        total = len(hosts)

        self.log(f"Starting export for {total} hosts...")

        for idx, host_id in enumerate(hosts, start=1):

            self.log(f"Processing host {host_id} ({idx}/{total})")

            df = self.db_call(host_id)

            if df is not None:
                self.write_parquet(df)

            self.progress(idx, total)

        self.log("Export completed successfully.")