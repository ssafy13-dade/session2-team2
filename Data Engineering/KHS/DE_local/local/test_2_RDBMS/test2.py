import json
import pandas as pd
from pathlib import Path
import re

# JSON 파일 로드
with open("../single_match_timeline.json", "r", encoding="utf-8") as f:
    data = json.load(f)

match_id = list(data.keys())[0]
match_data = data[match_id]
info = match_data["info"]
metadata = match_data["metadata"]
frames_list = info["frames"]

# match_number 정수 추출 (예: KR_123456 -> 123456)
match_number_match = re.search(r"\d+$", match_id)
match_number = int(match_number_match.group()) if match_number_match else None

# 저장 경로 설정
output_dir = Path("../csv_rdbms_style")
output_dir.mkdir(exist_ok=True)

# 1. matches
matches_df = pd.DataFrame([{
    "match_id": match_id,
    "match_number": match_number,
    "game_id": info.get("gameId"),
    "data_version": metadata.get("dataVersion"),
    "end_of_game_result": info.get("endOfGameResult"),
    "frame_interval": info.get("frameInterval")
}])
matches_df.to_csv(output_dir / "matches.csv", index=False)

# 2. participants
participants_df = pd.DataFrame([
    {
        "match_id": match_id,
        "match_number": match_number,
        "participant_id": p["participantId"],
        "puuid": p["puuid"]
    }
    for p in info.get("participants", [])
])
participants_df.to_csv(output_dir / "participants.csv", index=False)

# 3. frames
frames_df = pd.DataFrame([
    {"match_id": match_id, "match_number": match_number, "timestamp": frame["timestamp"]}
    for frame in frames_list
])
frames_df.to_csv(output_dir / "frames.csv", index=False)

# 4. participant_frames
participant_frame_rows = []
for frame in frames_list:
    frame_ts = frame["timestamp"]
    for pid_str, pf in frame.get("participantFrames", {}).items():
        part_id = int(pid_str)
        row = {
            "match_id": match_id,
            "match_number": match_number,
            "participant_id": part_id,
            "frame_timestamp": frame_ts,
            "current_gold": pf.get("currentGold"),
            "gold_per_second": pf.get("goldPerSecond"),
            "jungle_minions_killed": pf.get("jungleMinionsKilled"),
            "level": pf.get("level"),
            "minions_killed": pf.get("minionsKilled"),
            "time_enemy_spent_controlled": pf.get("timeEnemySpentControlled"),
            "total_gold": pf.get("totalGold"),
            "xp": pf.get("xp"),
            "position_x": pf.get("position", {}).get("x"),
            "position_y": pf.get("position", {}).get("y"),
        }
        for k, v in pf.get("championStats", {}).items():
            row[f"{k.lower()}"] = v
        for k, v in pf.get("damageStats", {}).items():
            row[f"{k[0].lower() + k[1:]}"] = v
        participant_frame_rows.append(row)
participant_frames_df = pd.DataFrame(participant_frame_rows)
participant_frames_df.to_csv(output_dir / "participant_frames.csv", index=False)

# 5. events + sub tables
events_rows = []
event_assists_rows = []
event_victim_damage_dealt_rows = []
event_victim_damage_received_rows = []

for frame in frames_list:
    frame_ts = frame["timestamp"]
    for event in frame.get("events", []):
        events_rows.append({
            "match_id": match_id,
            "match_number": match_number,
            "frame_timestamp": frame_ts,
            "timestamp": event.get("timestamp"),
            "real_timestamp": event.get("realTimestamp"),
            "type": event.get("type"),
            "participant_id": event.get("participantId"),
            "killer_id": event.get("killerId"),
            "victim_id": event.get("victimId"),
            "creator_id": event.get("creatorId"),
            "killer_team_id": event.get("killerTeamId"),
            "team_id": event.get("teamId"),
            "item_id": event.get("itemId"),
            "before_id": event.get("beforeId"),
            "after_id": event.get("afterId"),
            "skill_slot": event.get("skillSlot"),
            "level_up_type": event.get("levelUpType"),
            "level": event.get("level"),
            "ward_type": event.get("wardType"),
            "building_type": event.get("buildingType"),
            "tower_type": event.get("towerType"),
            "lane_type": event.get("laneType"),
            "monster_type": event.get("monsterType"),
            "monster_sub_type": event.get("monsterSubType"),
            "kill_streak_length": event.get("killStreakLength"),
            "multi_kill_length": event.get("multiKillLength"),
            "kill_type": event.get("killType"),
            "bounty": event.get("bounty"),
            "shutdown_bounty": event.get("shutdownBounty"),
            "gold_gain": event.get("goldGain"),
            "feat_type": event.get("featType"),
            "feat_value": event.get("featValue"),
            "winning_team": event.get("winningTeam"),
            "actual_start_time": event.get("actualStartTime"),
            "position_x": event.get("position", {}).get("x"),
            "position_y": event.get("position", {}).get("y")
        })

        if event.get("assistingParticipantIds"):
            for pid in event["assistingParticipantIds"]:
                event_assists_rows.append({
                    "match_id": match_id,
                    "match_number": match_number,
                    "frame_timestamp": frame_ts,
                    "event_timestamp": event.get("timestamp"),
                    "event_type": event.get("type"),
                    "participant_id": pid
                })

        if event.get("victimDamageDealt"):
            for idx, dmg in enumerate(event["victimDamageDealt"], start=1):
                event_victim_damage_dealt_rows.append({
                    "match_id": match_id,
                    "match_number": match_number,
                    "frame_timestamp": frame_ts,
                    "event_timestamp": event.get("timestamp"),
                    "instance": idx,
                    "basic": dmg.get("basic"),
                    "magic_damage": dmg.get("magicDamage"),
                    "physical_damage": dmg.get("physicalDamage"),
                    "true_damage": dmg.get("trueDamage"),
                    "name": dmg.get("name"),
                    "participant_id": dmg.get("participantId"),
                    "spell_name": dmg.get("spellName"),
                    "spell_slot": dmg.get("spellSlot"),
                    "type": dmg.get("type")
                })

        if event.get("victimDamageReceived"):
            for idx, dmg in enumerate(event["victimDamageReceived"], start=1):
                event_victim_damage_received_rows.append({
                    "match_id": match_id,
                    "match_number": match_number,
                    "frame_timestamp": frame_ts,
                    "event_timestamp": event.get("timestamp"),
                    "instance": idx,
                    "basic": dmg.get("basic"),
                    "magic_damage": dmg.get("magicDamage"),
                    "physical_damage": dmg.get("physicalDamage"),
                    "true_damage": dmg.get("trueDamage"),
                    "name": dmg.get("name"),
                    "participant_id": dmg.get("participantId"),
                    "spell_name": dmg.get("spellName"),
                    "spell_slot": dmg.get("spellSlot"),
                    "type": dmg.get("type")
                })

# 저장
pd.DataFrame(events_rows).to_csv(output_dir / "events.csv", index=False)
pd.DataFrame(event_assists_rows).to_csv(output_dir / "event_assists.csv", index=False)
pd.DataFrame(event_victim_damage_dealt_rows).to_csv(output_dir / "event_victim_damage_dealt.csv", index=False)
pd.DataFrame(event_victim_damage_received_rows).to_csv(output_dir / "event_victim_damage_received.csv", index=False)

print(f"✅ 모든 CSV가 저장되었습니다! 경로: {output_dir.resolve()}")
