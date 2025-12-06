"""
Tests for the High School Management System API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the API"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        name: {"participants": details["participants"].copy(), **{k: v for k, v in details.items() if k != "participants"}}
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        if name in activities:
            activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that getting activities returns 200 status"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that activities endpoint returns a dictionary"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that response contains expected activities"""
        response = client.get("/activities")
        data = response.json()
        
        # Check for some expected activities
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Basketball Team" in data
    
    def test_activity_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_existing_activity(self, client):
        """Test successful signup for an existing activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_adds_participant_to_list(self, client):
        """Test that signup actually adds participant to the activity"""
        email = "newstudent@mergington.edu"
        client.post(f"/activities/Art Club/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Art Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_duplicate_signup_fails(self, client):
        """Test that signing up twice for the same activity fails"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Drama Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Drama Club/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert data["detail"] == "Student already signed up for this activity"


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_existing_participant(self, client):
        """Test removing an existing participant from an activity"""
        # First, add a participant
        email = "removeme@mergington.edu"
        client.post(f"/activities/Science Olympiad/signup?email={email}")
        
        # Then remove them
        response = client.delete(f"/activities/Science Olympiad/participants/{email}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Science Olympiad" in data["message"]
    
    def test_remove_participant_actually_removes_from_list(self, client):
        """Test that removing a participant actually removes them from the list"""
        email = "willberemoved@mergington.edu"
        
        # Add participant
        client.post(f"/activities/Track and Field/signup?email={email}")
        
        # Verify they're in the list
        response = client.get("/activities")
        data = response.json()
        assert email in data["Track and Field"]["participants"]
        
        # Remove participant
        client.delete(f"/activities/Track and Field/participants/{email}")
        
        # Verify they're no longer in the list
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Track and Field"]["participants"]
    
    def test_remove_participant_from_nonexistent_activity(self, client):
        """Test removing a participant from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent Club/participants/test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_remove_nonexistent_participant(self, client):
        """Test removing a participant that isn't in the activity"""
        response = client.delete(
            "/activities/Debate Team/participants/notregistered@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Participant not found in this activity"
    
    def test_remove_preexisting_participant(self, client):
        """Test removing a participant that was already in the initial data"""
        # Michael is already in Chess Club
        response = client.delete(
            "/activities/Chess Club/participants/michael@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify they're removed
        response = client.get("/activities")
        data = response.json()
        assert "michael@mergington.edu" not in data["Chess Club"]["participants"]


class TestEndToEndScenarios:
    """End-to-end integration tests"""
    
    def test_complete_signup_and_removal_flow(self, client):
        """Test a complete flow of signing up and then removing a participant"""
        email = "fullflow@mergington.edu"
        activity = "Gym Class"
        
        # Get initial participant count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify count increased
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        
        # Remove participant
        response = client.delete(f"/activities/{activity}/participants/{email}")
        assert response.status_code == 200
        
        # Verify count returned to original
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count
    
    def test_multiple_signups_different_activities(self, client):
        """Test that a student can sign up for multiple different activities"""
        email = "multisport@mergington.edu"
        
        # Sign up for multiple activities
        response1 = client.post(f"/activities/Basketball Team/signup?email={email}")
        response2 = client.post(f"/activities/Track and Field/signup?email={email}")
        response3 = client.post(f"/activities/Gym Class/signup?email={email}")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        
        # Verify participant is in all three
        response = client.get("/activities")
        data = response.json()
        assert email in data["Basketball Team"]["participants"]
        assert email in data["Track and Field"]["participants"]
        assert email in data["Gym Class"]["participants"]
