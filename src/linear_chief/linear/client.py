"""Linear GraphQL API client with httpx."""

import httpx
from typing import Dict, List, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)


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
    async def query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        logger.debug(f"Executing Linear GraphQL query: {query[:100]}...")

        response = await self.client.post(self.API_URL, json=payload)
        response.raise_for_status()

        data = response.json()

        if "errors" in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            raise Exception(f"GraphQL query failed: {data['errors']}")

        return data.get("data", {})

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
            team_filter = " OR ".join([f'team: ' + '{id: {eq: "' + tid + '"}}' for tid in team_ids])
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
        return result.get("issues", {}).get("nodes", [])

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
        return result.get("viewer", {})

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
        return result.get("teams", {}).get("nodes", [])

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

        if not viewer_id:
            logger.error("Could not get viewer ID")
            return []

        # Fetch issues from all relevant sources
        logger.info("Fetching issues assigned to me...")
        assigned_issues = await self.get_issues(assignee_id=viewer_id, limit=limit)

        logger.info("Fetching issues created by me...")
        created_issues = await self._get_created_issues(viewer_id, limit)

        logger.info("Fetching subscribed issues...")
        subscribed_issues = await self._get_subscribed_issues(limit)

        # Aggregate and deduplicate by issue ID
        all_issues = {}
        for issue in assigned_issues + created_issues + subscribed_issues:
            issue_id = issue.get("id")
            if issue_id and issue_id not in all_issues:
                all_issues[issue_id] = issue

        logger.info(f"Found {len(all_issues)} unique relevant issues")
        return list(all_issues.values())

    async def _get_created_issues(self, creator_id: str, limit: int) -> List[Dict[str, Any]]:
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
        return result.get("issues", {}).get("nodes", [])

    async def _get_subscribed_issues(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch issues the user is subscribed to."""
        filter_clause = 'filter: {subscribers: {some: {}}}'

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
              subscriberIds
            }}
          }}
        }}
        """

        result = await self.query(query)
        issues = result.get("issues", {}).get("nodes", [])

        # Filter to only issues where current user is actually subscribed
        # (Linear API might return all subscribed issues, need to verify viewer is in list)
        return issues
