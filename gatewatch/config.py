import os
from dataclasses import dataclass


@dataclass
class Config:
    nvr_host: str
    nvr_user: str
    nvr_pass: str
    tg_token: str
    tg_chat_id: str
    cameras_file: str = "/data/cameras.json"
    db_path: str = "/data/gatewatch.db"
    snapshot_dir: str = "/data/snapshots"

    @classmethod
    def from_env(cls):
        e = os.environ
        return cls(e["NVR_HOST"], e["NVR_USER"], e["NVR_PASS"],
                   e["TG_TOKEN"], e["TG_CHAT_ID"])
