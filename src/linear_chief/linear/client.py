"""Linear GraphQL API client with httpx."""

import httpx
from typing import Dict, List, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from linear_chief.utils.logging import get_logger

logger = get_logger(__name__)


class LinearClient:
    """Client for interacting with the Linear GraphQL API."""

    API_URL = "https://api.linear.app/graphql"

    def __init__(self, api_key: str):
        """
        Initialize Linear API client.

        Args:
            api_key: Linear API key for authentication
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query against Linear API.

        Args:
            query: GraphQL query string
            variables: Optional variables for the query

        Returns:
            Query response data

        Raises:
            httpx.HTTPError: If the request fails
        """
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        logger.debug(f"Executing Linear GraphQL query: {query[:100]}...")

        response = await self.client.post(self.API_URL, json=payload)

        # Parse response even if HTTP error
        try:
            data = response.json()
        except Exception:
            data = {}

        # Log GraphQL errors before raising HTTP error
        if "errors" in data:
            logger.error(
                "GraphQL query failed",
                extra={
                    "service": "Linear",
                    "error_type": "GraphQLError",
                    "errors": data["errors"],
                },
            )
            raise Exception(f"GraphQL query failed: {data['errors']}")

        response.raise_for_status()

        # GraphQL responses are dynamically typed JSON - mypy can't verify structure
        return data.get("data", {})  # type: ignore[no-any-return]

    async def get_issues(
        self,
        team_ids: Optional[List[str]] = None,
        assignee_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetch issues from Linear.

        Args:
            team_ids: Optional list of team IDs to filter by
            assignee_id: Optional assignee user ID to filter by
            limit: Maximum number of issues to return

        Returns:
            List of issue dictionaries
        """
        filter_parts = []

        if team_ids:
            team_filter = " OR ".join(
                ["team: " + '{id: {eq: "' + tid + '"}}' for tid in team_ids]
            )
            filter_parts.append(f"or: [{team_filter}]")

        if assignee_id:
            filter_parts.append('assignee: {id: {eq: "' + assignee_id + '"}}')

        filter_str = ", ".join(filter_parts) if filter_parts else ""
        filter_clause = ("filter: {" + filter_str + "}") if filter_str else ""

        query = f"""
        query {{
          issues({filter_clause}, first: {limit}, orderBy: updatedAt) {{
            nodes {{
              id
              identifier
              title
              description
              priority
              priorityLabel
              url
              createdAt
              updatedAt
              completedAt
              canceledAt
              state {{
                id
                name
                type
              }}
              assignee {{
                id
                name
                email
              }}
              team {{
                id
                name
                key
              }}
              labels {{
                nodes {{
                  id
                  name
                  color
                }}
              }}
              comments {{
                nodes {{
                  id
                  body
                  createdAt
                  user {{
                    name
                  }}
                }}
              }}
            }}
          }}
        }}
        """

        result = await self.query(query)
        # GraphQL responses are dynamically typed
        return result.get("issues", {}).get("nodes", [])  # type: ignore[no-any-return]

    async def get_viewer(self) -> Dict[str, Any]:
        """
        Get the authenticated user (viewer) information.

        Returns:
            Dictionary with viewer information
        """
        query = """
        query {
          viewer {
            id
            name
            email
          }
        }
        """

        result = await self.query(query)
        # GraphQL responses are dynamically typed
        return result.get("viewer", {})  # type: ignore[no-any-return]

    async def get_teams(self) -> List[Dict[str, Any]]:
        """
        Fetch all teams accessible to the authenticated user.

        Returns:
            List of team dictionaries
        """
        query = """
        query {
          teams {
            nodes {
              id
              name
              key
              description
            }
          }
        }
        """

        result = await self.query(query)
        # GraphQL responses are dynamically typed
        return result.get("teams", {}).get("nodes", [])  # type: ignore[no-any-return]

    async def get_my_relevant_issues(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all issues relevant to the authenticated user:
        - Assigned to me
        - Created by me
        - Subscribed to
        - Commented by me

        Returns deduplicated list of issues.

        Args:
            limit: Maximum number of issues per category

        Returns:
            Deduplicated list of issue dictionaries
        """
        viewer = await self.get_viewer()
        viewer_id = viewer.get("id")
        viewer_email = viewer.get("email")

        if not viewer_id:
            logger.error("Could not get viewer ID")
            return []

        # Fetch issues from all relevant sources
        logger.info("Fetching issues assigned to me...")
        assigned_issues = await self.get_issues(assignee_id=viewer_id, limit=limit)

        logger.info("Fetching issues created by me...")
        created_issues = await self._get_created_issues(viewer_id, limit)

        logger.info("Fetching subscribed issues...")
        subscribed_issues = (
            await self._get_subscribed_issues(viewer_email, limit)
            if viewer_email
            else []
        )

        logger.info("Fetching issues I commented on...")
        commented_issues = await self._get_commented_issues(viewer_id, limit)

        # Aggregate and deduplicate by issue ID
        all_issues = {}
        for issue in (
            assigned_issues + created_issues + subscribed_issues + commented_issues
        ):
            issue_id = issue.get("id")
            if issue_id and issue_id not in all_issues:
                all_issues[issue_id] = issue

        logger.info(
            f"Found {len(all_issues)} unique relevant issues "
            f"(assigned: {len(assigned_issues)}, created: {len(created_issues)}, "
            f"subscribed: {len(subscribed_issues)}, commented: {len(commented_issues)})"
        )
        return list(all_issues.values())

    async def _get_created_issues(
        self, creator_id: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch issues created by specific user."""
        filter_clause = 'filter: {creator: {id: {eq: "' + creator_id + '"}}}'

        query = f"""
        query {{
          issues({filter_clause}, first: {limit}, orderBy: updatedAt) {{
            nodes {{
              id
              identifier
              title
              description
              priority
              priorityLabel
              url
              createdAt
              updatedAt
              completedAt
              canceledAt
              state {{
                id
                name
                type
              }}
              assignee {{
                id
                name
                email
              }}
              creator {{
                id
                name
                email
              }}
              team {{
                id
                name
                key
              }}
              labels {{
                nodes {{
                  id
                  name
                  color
                }}
              }}
              comments {{
                nodes {{
                  id
                  body
                  createdAt
                  user {{
                    name
                  }}
                }}
              }}
            }}
          }}
        }}
        """

        result = await self.query(query)
        # GraphQL responses are dynamically typed
        return result.get("issues", {}).get("nodes", [])  # type: ignore[no-any-return]

    async def _get_subscribed_issues(
        self, email: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch issues the user is subscribed to."""
        filter_clause = 'filter: {subscribers: {email: {eq: "' + email + '"}}}'

        query = f"""
        query {{
          issues({filter_clause}, first: {limit}, orderBy: updatedAt) {{
            nodes {{
              id
              identifier
              title
              description
              priority
              priorityLabel
              url
              createdAt
              updatedAt
              completedAt
              canceledAt
              state {{
                id
                name
                type
              }}
              assignee {{
                id
                name
                email
              }}
              creator {{
                id
                name
                email
              }}
              team {{
                id
                name
                key
              }}
              labels {{
                nodes {{
                  id
                  name
                  color
                }}
              }}
              comments {{
                nodes {{
                  id
                  body
                  createdAt
                  user {{
                    name
                  }}
                }}
              }}
              subscribers {{
                nodes {{
                  id
                  email
                }}
              }}
            }}
          }}
        }}
        """

        result = await self.query(query)
        # GraphQL responses are dynamically typed
        return result.get("issues", {}).get("nodes", [])  # type: ignore[no-any-return]

    async def _get_commented_issues(
        self, user_id: str, limit: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch issues the user has commented on.

        Strategy: Query comments by user, extract unique issue IDs,
        then fetch full issue details.

        Args:
            user_id: User ID to filter comments by
            limit: Maximum number of comments to fetch

        Returns:
            List of unique issues with user comments
        """
        # Step 1: Get all comments by this user
        query = f"""
        query {{
          comments(first: {limit}, filter: {{user: {{id: {{eq: "{user_id}"}}}}}}) {{
            nodes {{
              id
              issue {{
                id
                identifier
                title
                description
                priority
                priorityLabel
                url
                createdAt
                updatedAt
                completedAt
                canceledAt
                state {{
                  id
                  name
                  type
                }}
                assignee {{
                  id
                  name
                  email
                }}
                creator {{
                  id
                  name
                  email
                }}
                team {{
                  id
                  name
                  key
                }}
                labels {{
                  nodes {{
                    id
                    name
                    color
                  }}
                }}
                comments {{
                  nodes {{
                    id
                    body
                    createdAt
                    user {{
                      name
                    }}
                  }}
                }}
                subscribers {{
                  nodes {{
                    id
                    email
                  }}
                }}
              }}
            }}
          }}
        }}
        """

        result = await self.query(query)
        comments = result.get("comments", {}).get("nodes", [])

        # Step 2: Extract unique issues (deduplicate)
        issues_map = {}
        for comment in comments:
            issue = comment.get("issue")
            if issue:
                issue_id = issue.get("id")
                if issue_id and issue_id not in issues_map:
                    issues_map[issue_id] = issue

        return list(issues_map.values())

    async def get_issue_by_identifier(
        self, identifier: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single issue by its identifier (e.g., 'DMD-480', 'CSM-93').

        Uses GraphQL filter with team key and issue number for efficient querying.

        Args:
            identifier: Issue identifier (e.g., 'DMD-480')

        Returns:
            Issue dictionary with full details, or None if not found
        """
        # Extract team key and number from identifier (e.g., 'CSM-93' -> 'CSM', 93)
        if "-" not in identifier:
            logger.warning(f"Invalid identifier format: {identifier}")
            return None

        parts = identifier.split("-")
        team_key = parts[0]

        try:
            issue_number = int(parts[1])
        except (ValueError, IndexError):
            logger.warning(f"Invalid identifier format: {identifier}")
            return None

        # Query single issue using team key + number filter (efficient!)
        query = f"""
        query {{
          issues(filter: {{number: {{eq: {issue_number}}}, team: {{key: {{eq: "{team_key}"}}}}}}, first: 1) {{
            nodes {{
              id
              identifier
              title
              description
              priority
              priorityLabel
              url
              createdAt
              updatedAt
              completedAt
              canceledAt
              state {{
                id
                name
                type
              }}
              assignee {{
                id
                name
                email
              }}
              creator {{
                id
                name
                email
              }}
              team {{
                id
                name
                key
              }}
              labels {{
                nodes {{
                  id
                  name
                  color
                }}
              }}
              comments {{
                nodes {{
                  id
                  body
                  createdAt
                  user {{
                    name
                  }}
                }}
              }}
              subscribers {{
                nodes {{
                  id
                  email
                }}
              }}
            }}
          }}
        }}
        """

        try:
            result = await self.query(query)
            issues = result.get("issues", {}).get("nodes", [])

            # GraphQL filter ensures we get exactly the right issue (or nothing)
            if issues:
                return issues[0]  # type: ignore[no-any-return]

            logger.warning(f"Issue {identifier} not found")
            return None

        except Exception as e:
            logger.error(
                f"Failed to fetch issue {identifier}",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            return None
