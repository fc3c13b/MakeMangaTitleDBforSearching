"""チェックポイント管理モジュール"""
import json
import logging
import os

logger = logging.getLogger(__name__)


def save_checkpoint(path: str, last_group_id: int):
    """チェックポイントを保存（アトミック書き込みで破損防止）"""
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump({"last_group_id": last_group_id}, f)
        os.replace(tmp_path, path)
        logger.info(f"Checkpoint saved: last_group_id={last_group_id}")
    except Exception as e:
        logger.error(f"Checkpoint save failed: {e}", exc_info=True)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def load_checkpoint(path: str):
    """チェックポイントをロード。存在しない・破損している場合はNoneを返す"""
    if not os.path.exists(path):
        logger.debug(f"Checkpoint file not found: {path}")
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            cp = json.load(f)
        assert "last_group_id" in cp, "Missing last_group_id key"
        assert isinstance(cp["last_group_id"], int), "Invalid type for last_group_id"
        logger.info(f"Checkpoint loaded: last_group_id={cp['last_group_id']}")
        return cp
    except Exception as e:
        logger.error(f"Checkpoint load failed: {e}", exc_info=True)
        return None


def delete_checkpoint(path: str):
    """チェックポイントを削除（全件完了時）"""
    if os.path.exists(path):
        os.remove(path)
        logger.info("Checkpoint deleted (all groups processed)")