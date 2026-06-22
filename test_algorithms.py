import unittest
from server import calculate_rankings_list, propagate_playoff_winners, state

class TestTournamentAlgorithms(unittest.TestCase):

    def setUp(self):
        # Clear/Reset state for each test
        state["teams"] = []
        state["matches"] = []
        state["playoffBracket"]["matches"] = []
        state["settings"]["lockRankings"] = False
        state["settings"]["activeMatchId"] = None

    def test_ranking_calculations(self):
        # 1. Register 4 teams
        state["teams"] = [
            {"id": "t1", "name": "Bite Force", "robotName": "BF"},
            {"id": "t2", "name": "Tombstone", "robotName": "TS"},
            {"id": "t3", "name": "Minotaur", "robotName": "MN"},
            {"id": "t4", "name": "Witch Doctor", "robotName": "WD"}
        ]

        # 2. Add qualification matches with results
        # Match 1: t1 vs t2, Winner: t1
        # Match 2: t3 vs t4, Winner: t3
        # Match 3: t1 vs t3, Winner: t1
        # Match 4: t2 vs t4, Winner: t4
        state["matches"] = [
            {"id": "m1", "type": "quali", "teamAId": "t1", "teamBId": "t2", "winnerId": "t1", "status": "completed"},
            {"id": "m2", "type": "quali", "teamAId": "t3", "teamBId": "t4", "winnerId": "t3", "status": "completed"},
            {"id": "m3", "type": "quali", "teamAId": "t1", "teamBId": "t3", "winnerId": "t1", "status": "completed"},
            {"id": "m4", "type": "quali", "teamAId": "t2", "teamBId": "t4", "winnerId": "t4", "status": "completed"}
        ]

        # Calculate rankings
        rankings = calculate_rankings_list()
        
        # Rankings order check:
        # t1: Played 2, Won 2, Lost 0 -> Win Pct = 100%
        # t3: Played 2, Won 1, Lost 1 -> Win Pct = 50%
        # t4: Played 2, Won 1, Lost 1 -> Win Pct = 50%
        # t2: Played 2, Won 0, Lost 2 -> Win Pct = 0%
        
        # Tie breaker check between t3 and t4:
        # t3 played opponents: t4 (50% win) and t1 (100% win) -> t3 AOWP = (50 + 100)/2 = 75%
        # t4 played opponents: t3 (50% win) and t2 (0% win)   -> t4 AOWP = (50 + 0)/2 = 25%
        # Therefore, t3 should rank #2, and t4 should rank #3
        
        self.assertEqual(rankings[0]["id"], "t1") # Rank 1: Bite Force
        self.assertEqual(rankings[1]["id"], "t3") # Rank 2: Minotaur
        self.assertEqual(rankings[2]["id"], "t4") # Rank 3: Witch Doctor
        self.assertEqual(rankings[3]["id"], "t2") # Rank 4: Tombstone
        
        self.assertEqual(rankings[1]["aowp"], 75.0)
        self.assertEqual(rankings[2]["aowp"], 25.0)

    def test_playoff_propagation(self):
        state["teams"] = [
            {"id": "t1", "name": "Bite Force", "robotName": "BF"},
            {"id": "t2", "name": "Tombstone", "robotName": "TS"},
            {"id": "t3", "name": "Minotaur", "robotName": "MN"},
            {"id": "t4", "name": "Witch Doctor", "robotName": "WD"}
        ]
        # Let's mock a simple ranking results where t1=Rank1, t2=Rank2, t3=Rank3, t4=Rank4
        # We can simulate this by setting quali matches where rankings naturally fall in this order
        state["matches"] = [
            {"id": "m1", "type": "quali", "teamAId": "t1", "teamBId": "t2", "winnerId": "t1", "status": "completed"},
            {"id": "m2", "type": "quali", "teamAId": "t3", "teamBId": "t4", "winnerId": "t3", "status": "completed"},
            {"id": "m3", "type": "quali", "teamAId": "t2", "teamBId": "t3", "winnerId": "t2", "status": "completed"},
            {"id": "m4", "type": "quali", "teamAId": "t1", "teamBId": "t4", "winnerId": "t1", "status": "completed"}
        ]
        # Rankings order: t1 (100%), t2 (50%), t3 (50%), t4 (0%)
        # Let's double check rankings:
        # t2 played t1 (100%), t3 (50%) -> AOWP = 75%
        # t3 played t4 (0%), t2 (50%) -> AOWP = 25%
        # So t2 is rank 2, t3 is rank 3.
        
        # Design Playoff Bracket
        # P1: Semi-final (Rank 1 vs Rank 4) -> Should resolve to t1 vs t4
        # P2: Grand Finals (Winner of P1 vs Rank 2) -> Should resolve to (Winner of P1) vs t2
        state["matches"] += [
            {
                "id": "p1",
                "type": "playoff",
                "name": "Semi Final",
                "slotA": {"type": "rank", "value": 1},
                "slotB": {"type": "rank", "value": 4},
                "teamAId": None,
                "teamBId": None,
                "winnerId": None,
                "status": "scheduled"
            },
            {
                "id": "p2",
                "type": "playoff",
                "name": "Grand Final",
                "slotA": {"type": "match_winner", "value": "p1"},
                "slotB": {"type": "rank", "value": 2},
                "teamAId": None,
                "teamBId": None,
                "winnerId": None,
                "status": "scheduled"
            }
        ]
        
        # Turn lock rankings ON
        state["settings"]["lockRankings"] = True
        
        # Propagate
        propagate_playoff_winners()
        
        # Verify slots resolved
        playoff_matches = [m for m in state["matches"] if m.get("type") != "quali"]
        p1 = playoff_matches[0]
        p2 = playoff_matches[1]
        
        self.assertEqual(p1["teamAId"], "t1")
        self.assertEqual(p1["teamBId"], "t4")
        self.assertEqual(p2["teamBId"], "t2")
        self.assertIsNone(p2["teamAId"]) # P1 is not completed, so teamAId of Grand Final must be None
        
        # Play P1 and set winner as t1
        p1["winnerId"] = "t1"
        p1["status"] = "completed"
        
        # Propagate again
        propagate_playoff_winners()
        
        # Verify Grand Final teamAId resolved to t1
        self.assertEqual(p2["teamAId"], "t1")

if __name__ == '__main__':
    unittest.main()
