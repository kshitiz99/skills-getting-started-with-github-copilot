"""
Tests for the Mergington High School API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    activities.clear()
    activities.update({
        "Soccer Team": {
            "description": "Competitive soccer training and inter-school matches",
            "schedule": "Mondays and Wednesdays, 3:30 PM - 5:00 PM",
            "max_participants": 25,
            "participants": ["james@mergington.edu", "lucas@mergington.edu"]
        },
        "Basketball Club": {
            "description": "Basketball practice and tournament preparation",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 15,
            "participants": ["alex@mergington.edu", "ryan@mergington.edu"]
        },
        "Art Studio": {
            "description": "Painting, drawing, and mixed media art projects",
            "schedule": "Wednesdays, 3:00 PM - 5:00 PM",
            "max_participants": 18,
            "participants": ["lily@mergington.edu", "grace@mergington.edu"]
        }
    })
    yield


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that the root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        assert "Soccer Team" in data
        assert "Basketball Club" in data
        assert "Art Studio" in data
        assert len(data) == 3
    
    def test_get_activities_returns_correct_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        soccer = data["Soccer Team"]
        assert "description" in soccer
        assert "schedule" in soccer
        assert "max_participants" in soccer
        assert "participants" in soccer
        assert isinstance(soccer["participants"], list)
        assert soccer["max_participants"] == 25
        assert len(soccer["participants"]) == 2


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client):
        """Test successful signup for an activity"""
        response = client.post("/activities/Soccer Team/signup?email=new-student@mergington.edu")
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "new-student@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "new-student@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post("/activities/Nonexistent Activity/signup?email=student@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_participant(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        # First signup should succeed
        response1 = client.post("/activities/Soccer Team/signup?email=new-student@mergington.edu")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post("/activities/Soccer Team/signup?email=new-student@mergington.edu")
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_with_existing_participant(self, client):
        """Test that existing participants cannot sign up again"""
        response = client.post("/activities/Soccer Team/signup?email=james@mergington.edu")
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]


class TestUnregisterFromActivity:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_successful(self, client):
        """Test successful unregistration from an activity"""
        response = client.delete("/activities/Soccer Team/unregister?email=james@mergington.edu")
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "james@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "james@mergington.edu" not in activities_data["Soccer Team"]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregister from an activity that doesn't exist"""
        response = client.delete("/activities/Nonexistent Activity/unregister?email=student@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_participant_not_in_activity(self, client):
        """Test unregistering a participant who is not signed up"""
        response = client.delete("/activities/Soccer Team/unregister?email=not-registered@mergington.edu")
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_signup_and_unregister_workflow(self, client):
        """Test the complete workflow of signing up and unregistering"""
        email = "workflow-test@mergington.edu"
        
        # Sign up
        signup_response = client.post(f"/activities/Basketball Club/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signed up
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Basketball Club"]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/Basketball Club/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Basketball Club"]["participants"]


class TestActivityCapacity:
    """Tests for activity capacity management"""
    
    def test_participants_count_matches_list(self, client):
        """Test that the participant count matches the list length"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            participants = activity_data["participants"]
            max_participants = activity_data["max_participants"]
            assert len(participants) <= max_participants
