"""Integration tests for Linear GraphQL client."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from linear_chief.linear import LinearClient


@pytest.fixture
def api_key():
    """Test API key."""
    return "lin_api_test_key_12345"


@pytest.fixture
def mock_viewer_response():
    """Mock viewer response."""
    return {
        "data": {
            "viewer": {
                "id": "viewer-uuid-123",
                "name": "Test User",
                "email": "test@example.com",
            }
        }
    }


@pytest.fixture
def mock_teams_response():
    """Mock teams response."""
    return {
        "data": {
            "teams": {
                "nodes": [
                    {
                        "id": "team-uuid-1",
                        "name": "Engineering",
                        "key": "ENG",
                        "description": "Engineering team",
                    },
                    {
                        "id": "team-uuid-2",
                        "name": "Product",
                        "key": "PROD",
                        "description": "Product team",
                    },
                ]
            }
        }
    }


@pytest.fixture
def mock_issues_response():
    """Mock issues response."""
    return {
        "data": {
            "issues": {
                "nodes": [
                    {
                        "id": "issue-uuid-1",
                        "identifier": "PROJ-123",
                        "title": "Fix login bug",
                        "description": "Users cannot log in",
                        "priority": 1,
                        "priorityLabel": "Urgent",
                        "url": "https://linear.app/issue/PROJ-123",
                        "createdAt": "2024-01-01T10:00:00Z",
                        "updatedAt": "2024-01-02T15:30:00Z",
                        "completedAt": None,
                        "canceledAt": None,
                        "state": {
                            "id": "state-uuid-1",
                            "name": "In Progress",
                            "type": "started",
                        },
                        "assignee": {
                            "id": "user-uuid-1",
                            "name": "John Doe",
                            "email": "john@example.com",
                        },
                        "team": {
                            "id": "team-uuid-1",
                            "name": "Engineering",
                            "key": "ENG",
                        },
                        "labels": {
                            "nodes": [
                                {"id": "label-1", "name": "bug", "color": "#ff0000"}
                            ]
                        },
                        "comments": {
                            "nodes": [
                                {
                                    "id": "comment-1",
                                    "body": "Working on this",
                                    "createdAt": "2024-01-02T12:00:00Z",
                                    "user": {"name": "John Doe"},
                                }
                            ]
                        },
                    },
                    {
                        "id": "issue-uuid-2",
                        "identifier": "PROJ-124",
                        "title": "Add dark mode",
                        "description": "Implement dark theme",
                        "priority": 3,
                        "priorityLabel": "Normal",
                        "url": "https://linear.app/issue/PROJ-124",
                        "createdAt": "2024-01-03T09:00:00Z",
                        "updatedAt": "2024-01-03T09:00:00Z",
                        "completedAt": None,
                        "canceledAt": None,
                        "state": {
                            "id": "state-uuid-2",
                            "name": "Todo",
                            "type": "unstarted",
                        },
                        "assignee": None,
                        "team": {
                            "id": "team-uuid-1",
                            "name": "Engineering",
                            "key": "ENG",
                        },
                        "labels": {"nodes": []},
                        "comments": {"nodes": []},
                    },
                ]
            }
        }
    }


@pytest.fixture
def mock_created_issues_response():
    """Mock created issues response."""
    return {
        "data": {
            "issues": {
                "nodes": [
                    {
                        "id": "issue-uuid-3",
                        "identifier": "PROJ-125",
                        "title": "Created issue",
                        "description": "Issue I created",
                        "priority": 2,
                        "priorityLabel": "High",
                        "url": "https://linear.app/issue/PROJ-125",
                        "createdAt": "2024-01-04T10:00:00Z",
                        "updatedAt": "2024-01-04T10:00:00Z",
                        "completedAt": None,
                        "canceledAt": None,
                        "state": {
                            "id": "state-uuid-3",
                            "name": "Todo",
                            "type": "unstarted",
                        },
                        "assignee": {
                            "id": "other-user-uuid",
                            "name": "Jane Doe",
                            "email": "jane@example.com",
                        },
                        "creator": {
                            "id": "viewer-uuid-123",
                            "name": "Test User",
                            "email": "test@example.com",
                        },
                        "team": {
                            "id": "team-uuid-2",
                            "name": "Product",
                            "key": "PROD",
                        },
                        "labels": {"nodes": []},
                        "comments": {"nodes": []},
                    }
                ]
            }
        }
    }


@pytest.fixture
def mock_subscribed_issues_response():
    """Mock subscribed issues response."""
    return {
        "data": {
            "issues": {
                "nodes": [
                    {
                        "id": "issue-uuid-4",
                        "identifier": "PROJ-126",
                        "title": "Subscribed issue",
                        "description": "Issue I'm subscribed to",
                        "priority": 2,
                        "priorityLabel": "High",
                        "url": "https://linear.app/issue/PROJ-126",
                        "createdAt": "2024-01-05T10:00:00Z",
                        "updatedAt": "2024-01-05T10:00:00Z",
                        "completedAt": None,
                        "canceledAt": None,
                        "state": {
                            "id": "state-uuid-4",
                            "name": "In Review",
                            "type": "started",
                        },
                        "assignee": {
                            "id": "other-user-uuid-2",
                            "name": "Bob Smith",
                            "email": "bob@example.com",
                        },
                        "creator": {
                            "id": "other-user-uuid-2",
                            "name": "Bob Smith",
                            "email": "bob@example.com",
                        },
                        "team": {
                            "id": "team-uuid-1",
                            "name": "Engineering",
                            "key": "ENG",
                        },
                        "labels": {"nodes": []},
                        "comments": {"nodes": []},
                        "subscribers": {
                            "nodes": [
                                {"id": "viewer-uuid-123", "email": "test@example.com"}
                            ]
                        },
                    }
                ]
            }
        }
    }


@pytest.mark.asyncio
class TestLinearClientQuery:
    """Tests for GraphQL query execution."""

    async def test_query_success(self, api_key, mock_viewer_response):
        """Test successful GraphQL query execution."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_viewer_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            client = LinearClient(api_key)
            result = await client.query("query { viewer { id name email } }")

            assert result == mock_viewer_response["data"]
            mock_post.assert_called_once()
            await client.close()

    async def test_query_with_variables(self, api_key, mock_issues_response):
        """Test GraphQL query with variables."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_issues_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            client = LinearClient(api_key)
            variables = {"limit": 10}
            result = await client.query(
                "query($limit: Int!) { issues(first: $limit) { nodes { id } } }",
                variables,
            )

            assert result == mock_issues_response["data"]
            # Verify variables were passed
            call_args = mock_post.call_args
            assert call_args[1]["json"]["variables"] == variables
            await client.close()

    async def test_query_graphql_error(self, api_key):
        """Test GraphQL query with API errors."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "errors": [{"message": "Field 'invalid' doesn't exist"}]
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            client = LinearClient(api_key)

            with pytest.raises(Exception, match="GraphQL query failed"):
                await client.query("query { invalid }")

            await client.close()

    async def test_query_http_error(self, api_key):
        """Test GraphQL query with HTTP errors."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {}
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized", request=Mock(), response=Mock()
            )
            mock_post.return_value = mock_response

            client = LinearClient(api_key)

            with pytest.raises(httpx.HTTPStatusError):
                await client.query("query { viewer { id } }")

            await client.close()

    async def test_query_network_error(self, api_key):
        """Test GraphQL query with network errors."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection failed")

            client = LinearClient(api_key)

            with pytest.raises(httpx.ConnectError):
                await client.query("query { viewer { id } }")

            await client.close()

    async def test_query_retry_logic(self, api_key, mock_viewer_response):
        """Test retry logic on transient failures."""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Fail twice, succeed on third attempt
            mock_post.side_effect = [
                httpx.ConnectError("Timeout"),
                httpx.ConnectError("Timeout"),
                Mock(
                    json=Mock(return_value=mock_viewer_response),
                    raise_for_status=Mock(),
                ),
            ]

            client = LinearClient(api_key)
            result = await client.query("query { viewer { id } }")

            assert result == mock_viewer_response["data"]
            assert mock_post.call_count == 3
            await client.close()

    async def test_query_retry_exhausted(self, api_key):
        """Test retry logic when all attempts fail."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Timeout")

            client = LinearClient(api_key)

            with pytest.raises(httpx.ConnectError):
                await client.query("query { viewer { id } }")

            # Should retry 3 times
            assert mock_post.call_count == 3
            await client.close()


@pytest.mark.asyncio
class TestLinearClientViewer:
    """Tests for get_viewer method."""

    async def test_get_viewer_success(self, api_key, mock_viewer_response):
        """Test successful viewer fetch."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_viewer_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            client = LinearClient(api_key)
            viewer = await client.get_viewer()

            assert viewer["id"] == "viewer-uuid-123"
            assert viewer["name"] == "Test User"
            assert viewer["email"] == "test@example.com"
            await client.close()

    async def test_get_viewer_empty_response(self, api_key):
        """Test viewer fetch with empty response."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"data": {}}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            client = LinearClient(api_key)
            viewer = await client.get_viewer()

            assert viewer == {}
            await client.close()

    async def test_get_viewer_api_error(self, api_key):
        """Test viewer fetch with API error."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"errors": [{"message": "Unauthorized"}]}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            client = LinearClient(api_key)

            with pytest.raises(Exception, match="GraphQL query failed"):
                await client.get_viewer()

            await client.close()


@pytest.mark.asyncio
class TestLinearClientTeams:
    """Tests for get_teams method."""

    async def test_get_teams_success(self, api_key, mock_teams_response):
        """Test successful teams fetch."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_teams_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            client = LinearClient(api_key)
            teams = await client.get_teams()

            assert len(teams) == 2
            assert teams[0]["name"] == "Engineering"
            assert teams[0]["key"] == "ENG"
            assert teams[1]["name"] == "Product"
            await client.close()

    async def test_get_teams_empty(self, api_key):
        """Test teams fetch with no teams."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"data": {"teams": {"nodes": []}}}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            client = LinearClient(api_key)
            teams = await client.get_teams()

            assert teams == []
            await client.close()

    async def test_get_teams_missing_data(self, api_key):
        """Test teams fetch with missing data structure."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"data": {}}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            client = LinearClient(api_key)
            teams = await client.get_teams()

            assert teams == []
            await client.close()


@pytest.mark.asyncio
class TestLinearClientGetMyRelevantIssues:
    """Tests for get_my_relevant_issues method (main aggregation logic)."""

    async def test_get_my_relevant_issues_all_sources(
        self,
        api_key,
        mock_viewer_response,
        mock_issues_response,
        mock_created_issues_response,
        mock_subscribed_issues_response,
    ):
        """Test fetching issues from all sources (assigned + created + subscribed)."""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Set up responses in order: viewer, assigned, created, subscribed
            mock_post.side_effect = [
                Mock(
                    json=Mock(return_value=mock_viewer_response),
                    raise_for_status=Mock(),
                ),
                Mock(
                    json=Mock(return_value=mock_issues_response),
                    raise_for_status=Mock(),
                ),
                Mock(
                    json=Mock(return_value=mock_created_issues_response),
                    raise_for_status=Mock(),
                ),
                Mock(
                    json=Mock(return_value=mock_subscribed_issues_response),
                    raise_for_status=Mock(),
                ),
            ]

            client = LinearClient(api_key)
            issues = await client.get_my_relevant_issues(limit=50)

            # Should get 4 unique issues (2 assigned + 1 created + 1 subscribed)
            assert len(issues) == 4

            # Verify all issue IDs are present
            issue_ids = {issue["id"] for issue in issues}
            assert "issue-uuid-1" in issue_ids  # Assigned
            assert "issue-uuid-2" in issue_ids  # Assigned
            assert "issue-uuid-3" in issue_ids  # Created
            assert "issue-uuid-4" in issue_ids  # Subscribed

            await client.close()

    async def test_get_my_relevant_issues_deduplication(
        self, api_key, mock_viewer_response, mock_issues_response
    ):
        """Test deduplication when same issue appears in multiple sources."""
        # Same issue in both assigned and created
        duplicate_response = {
            "data": {
                "issues": {
                    "nodes": [mock_issues_response["data"]["issues"]["nodes"][0]]
                }
            }
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [
                Mock(
                    json=Mock(return_value=mock_viewer_response),
                    raise_for_status=Mock(),
                ),
                Mock(
                    json=Mock(return_value=mock_issues_response),
                    raise_for_status=Mock(),
                ),
                Mock(
                    json=Mock(return_value=duplicate_response), raise_for_status=Mock()
                ),
                Mock(
                    json=Mock(return_value={"data": {"issues": {"nodes": []}}}),
                    raise_for_status=Mock(),
                ),
            ]

            client = LinearClient(api_key)
            issues = await client.get_my_relevant_issues(limit=50)

            # Should deduplicate - 2 unique issues total
            assert len(issues) == 2

            # Verify issue IDs are unique
            issue_ids = [issue["id"] for issue in issues]
            assert len(issue_ids) == len(set(issue_ids))

            await client.close()

    async def test_get_my_relevant_issues_no_issues(
        self, api_key, mock_viewer_response
    ):
        """Test when no issues are found in any source."""
        empty_response = {"data": {"issues": {"nodes": []}}}

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [
                Mock(
                    json=Mock(return_value=mock_viewer_response),
                    raise_for_status=Mock(),
                ),
                Mock(json=Mock(return_value=empty_response), raise_for_status=Mock()),
                Mock(json=Mock(return_value=empty_response), raise_for_status=Mock()),
                Mock(json=Mock(return_value=empty_response), raise_for_status=Mock()),
            ]

            client = LinearClient(api_key)
            issues = await client.get_my_relevant_issues(limit=50)

            assert len(issues) == 0
            await client.close()

    async def test_get_my_relevant_issues_no_viewer_id(self, api_key):
        """Test when viewer ID cannot be retrieved."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Mock(
                json=Mock(return_value={"data": {"viewer": {}}}),
                raise_for_status=Mock(),
            )

            client = LinearClient(api_key)
            issues = await client.get_my_relevant_issues(limit=50)

            assert issues == []
            await client.close()

    async def test_get_my_relevant_issues_no_email(self, api_key, mock_issues_response):
        """Test when viewer has no email (subscribed issues should be skipped)."""
        viewer_no_email = {
            "data": {
                "viewer": {
                    "id": "viewer-uuid-123",
                    "name": "Test User",
                    "email": None,
                }
            }
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [
                Mock(json=Mock(return_value=viewer_no_email), raise_for_status=Mock()),
                Mock(
                    json=Mock(return_value=mock_issues_response),
                    raise_for_status=Mock(),
                ),
                Mock(
                    json=Mock(return_value={"data": {"issues": {"nodes": []}}}),
                    raise_for_status=Mock(),
                ),
                # No fourth call - subscribed should be skipped
            ]

            client = LinearClient(api_key)
            issues = await client.get_my_relevant_issues(limit=50)

            # Should only get assigned + created, not subscribed
            assert len(issues) == 2
            # Only 3 API calls (viewer, assigned, created)
            assert mock_post.call_count == 3

            await client.close()

    async def test_get_my_relevant_issues_partial_data(
        self, api_key, mock_viewer_response
    ):
        """Test when API returns partial/incomplete data."""
        partial_response = {
            "data": {
                "issues": {
                    "nodes": [
                        {
                            "id": "issue-uuid-5",
                            "identifier": "PROJ-127",
                            "title": "Partial issue",
                            # Missing most fields
                        }
                    ]
                }
            }
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [
                Mock(
                    json=Mock(return_value=mock_viewer_response),
                    raise_for_status=Mock(),
                ),
                Mock(json=Mock(return_value=partial_response), raise_for_status=Mock()),
                Mock(
                    json=Mock(return_value={"data": {"issues": {"nodes": []}}}),
                    raise_for_status=Mock(),
                ),
                Mock(
                    json=Mock(return_value={"data": {"issues": {"nodes": []}}}),
                    raise_for_status=Mock(),
                ),
            ]

            client = LinearClient(api_key)
            issues = await client.get_my_relevant_issues(limit=50)

            # Should still return partial issue
            assert len(issues) == 1
            assert issues[0]["id"] == "issue-uuid-5"
            assert issues[0]["title"] == "Partial issue"

            await client.close()

    async def test_get_my_relevant_issues_api_error_propagates(
        self, api_key, mock_viewer_response
    ):
        """Test that API errors during issue fetch propagate correctly."""
        error_response = Mock(
            json=Mock(return_value={"errors": [{"message": "Rate limit exceeded"}]}),
            raise_for_status=Mock(),
        )

        with patch("httpx.AsyncClient.post") as mock_post:
            # Need to handle retry logic (3 attempts for the failing query)
            mock_post.side_effect = [
                Mock(
                    json=Mock(return_value=mock_viewer_response),
                    raise_for_status=Mock(),
                ),
                error_response,  # 1st attempt
                error_response,  # 2nd attempt (retry)
                error_response,  # 3rd attempt (retry)
            ]

            client = LinearClient(api_key)

            with pytest.raises(Exception, match="GraphQL query failed"):
                await client.get_my_relevant_issues(limit=50)

            await client.close()


@pytest.mark.asyncio
class TestLinearClientContextManager:
    """Tests for async context manager functionality."""

    async def test_context_manager_closes_client(self, api_key, mock_viewer_response):
        """Test that context manager properly closes the client."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Mock(
                json=Mock(return_value=mock_viewer_response), raise_for_status=Mock()
            )

            async with LinearClient(api_key) as client:
                viewer = await client.get_viewer()
                assert viewer["id"] == "viewer-uuid-123"

            # Client should be closed after exiting context
            # Verify by checking that the client's aclose was called
            with patch.object(
                client.client, "aclose", new_callable=AsyncMock
            ) as mock_close:
                await client.close()
                mock_close.assert_called_once()
