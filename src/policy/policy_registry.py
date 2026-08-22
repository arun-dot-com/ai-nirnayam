import sqlite3
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta
logger = logging.getLogger(__name__)

class PolicyRegistry:
    """
    A lightweight SQLite-based registry to store and verify active motor insurance policies.
    Acts as the gatekeeper before claim adjudication.
    """
    
    def __init__(self, db_path: str = "data/nirnayam_policies.db"):
        self.db_path = db_path
        self._init_db()
        self._seed_mock_data() # Seeds realistic data for testing

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Creates the policy table if it doesn't exist."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS policies (
                    policy_number TEXT PRIMARY KEY,
                    vehicle_rc TEXT UNIQUE NOT NULL,
                    owner_name TEXT NOT NULL,
                    policy_start_date TEXT NOT NULL,
                    policy_end_date TEXT NOT NULL,
                    has_zero_dep INTEGER DEFAULT 0,
                    has_engine_protect INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'ACTIVE'
                )
            """)
    def verify_by_policy_number(self, policy_number: str) -> Dict[str, Any]:
        """Checks if a specific policy number exists and is active."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM policies WHERE policy_number = ?", (policy_number,))
            policy = cursor.fetchone()
            
        if not policy:
            return {"status": "NOT_FOUND", "message": f"Invalid Policy Number: {policy_number}. No record found."}
            
        policy_dict = dict(policy)
        end_date = datetime.strptime(policy_dict["policy_end_date"], "%Y-%m-%d").date()
        
        if end_date < date.today() or policy_dict["status"] == "EXPIRED":
            return {
                "status": "EXPIRED", 
                "message": f"Policy {policy_dict['policy_number']} expired on {policy_dict['policy_end_date']}. Claim cannot be processed.",
                "policy_details": policy_dict
            }
            
        return {
            "status": "ACTIVE",
            "message": f"✅ Active Policy: {policy_dict['policy_number']} (Owner: {policy_dict['owner_name']})",
            "policy_details": {
                "policy_number": policy_dict["policy_number"],
                "owner_name": policy_dict["owner_name"],
                "vehicle_rc": policy_dict["vehicle_rc"],
                "has_zero_dep": bool(policy_dict["has_zero_dep"]),
                "has_engine_protect": bool(policy_dict["has_engine_protect"])
            }
        }
    def _seed_mock_data(self):
        """Inserts a few realistic policies for testing (only if empty)."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM policies")
            if cursor.fetchone()[0] == 0:
                # Generate dynamic dates so test policies don't expire
                today = date.today()
                active_end_date = (today + timedelta(days=180)).strftime("%Y-%m-%d") # Valid for 6 months
                expired_end_date = (today - timedelta(days=30)).strftime("%Y-%m-%d") # Expired 1 month ago
                start_date = (today - timedelta(days=60)).strftime("%Y-%m-%d")       # Started 2 months ago
                
                mock_policies = [
                    # POL-MH-9981: Has Zero Dep, NO Engine Protect
                    ("POL-MH-9981", "MH02AB1234", "Rahul Sharma", start_date, active_end_date, 1, 0, "ACTIVE"), 
                    # POL-DL-4432: Has Zero Dep AND Engine Protect (Comprehensive)
                    ("POL-DL-4432", "DL3CAB9999", "Priya Reddy", start_date, active_end_date, 1, 1, "ACTIVE"),  
                    # POL-KA-1102: EXPIRED Policy
                    ("POL-KA-1102", "KA03MN1234", "Arun Kumar", start_date, expired_end_date, 0, 0, "EXPIRED"), 
                    # POL-TN-8877: NO Zero Dep, Has Engine Protect
                    ("POL-TN-8877", "TN09ZZ8888", "Sneha Iyer", start_date, active_end_date, 0, 1, "ACTIVE")   
                ]
                conn.executemany("""
                    INSERT INTO policies (policy_number, vehicle_rc, owner_name, policy_start_date, 
                                          policy_end_date, has_zero_dep, has_engine_protect, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, mock_policies)
                logger.info("Seeded mock policy data into SQLite registry with dynamic dates.")
                
    def verify_coverage(self, vehicle_rc: str) -> Dict[str, Any]:
        """
        Checks if a vehicle has an active policy and returns the coverage details.
        """
        rc_clean = vehicle_rc.replace(" ", "").upper()
        
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM policies WHERE REPLACE(vehicle_rc, ' ', '') = ?", 
                (rc_clean,)
            )
            policy = cursor.fetchone()
            
        if not policy:
            return {"status": "NOT_FOUND", "message": f"No policy found for vehicle {vehicle_rc}."}
            
        policy_dict = dict(policy)
        
        # Check if policy is actually active based on dates
        end_date = datetime.strptime(policy_dict["policy_end_date"], "%Y-%m-%d").date()
        if end_date < date.today() or policy_dict["status"] == "EXPIRED":
            return {
                "status": "EXPIRED", 
                "message": f"Policy {policy_dict['policy_number']} expired on {policy_dict['policy_end_date']}.",
                "policy_details": policy_dict
            }
            
        return {
            "status": "ACTIVE",
            "message": "Policy is active and valid.",
            "policy_details": {
                "policy_number": policy_dict["policy_number"],
                "owner_name": policy_dict["owner_name"],
                "has_zero_dep": bool(policy_dict["has_zero_dep"]),
                "has_engine_protect": bool(policy_dict["has_engine_protect"])
            }
        }

    def add_policy(self, policy_number: str, vehicle_rc: str, owner_name: str, 
                   start_date: str, end_date: str, zero_dep: bool, engine_protect: bool):
        """Adds a new policy to the registry."""
        with self._get_conn() as conn:
            try:
                conn.execute("""
                    INSERT INTO policies (policy_number, vehicle_rc, owner_name, policy_start_date, 
                                          policy_end_date, has_zero_dep, has_engine_protect, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                """, (policy_number, vehicle_rc.replace(" ", "").upper(), owner_name, start_date, end_date, int(zero_dep), int(engine_protect)))
                return True, "Policy added successfully."
            except sqlite3.IntegrityError:
                return False, "Policy Number or Vehicle RC already exists."