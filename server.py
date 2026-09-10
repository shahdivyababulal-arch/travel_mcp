"""Local MCP server for the travel planner.

Run with ``python -m mcp_server.server`` to expose the tools over Streamable
HTTP. The optional ``--transport stdio`` mode remains available for direct MCP
clients that manage the server as a subprocess.
"""
import logging
import argparse
import time

from mcp.server.fastmcp import FastMCP

from config.settings import settings
from logging_config.logger import configure_logging, configure_tracing, event
from observability.metrics import record_tool
from observability.span_data import summarize
from mcp_server.tools.attractions import search_attractions as _search_attractions
from mcp_server.tools.budget import calculate_budget as _calculate_budget
from mcp_server.tools.itinerary import create_itinerary as _create_itinerary
from mcp_server.tools.restaurants import search_restaurants as _search_restaurants
from mcp_server.tools.weather import get_weather as _get_weather

logger = logging.getLogger("travel.mcp")
mcp = FastMCP("local-travel-tools", host=settings.mcp_host, port=settings.mcp_port)


def _logged(name: str, fn, **kwargs):
    from opentelemetry import trace
    started = time.perf_counter()
    with trace.get_tracer("travel.mcp").start_as_current_span(
            f"mcp.tool.{name}",
            attributes={
                "mcp.tool.name": name,
                "mcp.tool.input": summarize(kwargs),
            }):
        try:
            event(logger, "mcp_tool_execution_started", tool_name=name)
            result = fn(**kwargs)
            trace.get_current_span().set_attribute(
                "mcp.tool.output", summarize(result))
            record_tool(name, (time.perf_counter() - started) * 1000, status="success")
            event(logger, "mcp_tool_execution_completed", tool_name=name, status="success")
            return result
        except Exception as error:
            record_tool(name, (time.perf_counter() - started) * 1000, status="failure")
            trace.get_current_span().record_exception(error)
            trace.get_current_span().set_status(trace.StatusCode.ERROR, str(error))
            trace.get_current_span().set_attribute("mcp.tool.error", str(error))
            event(logger, "mcp_tool_execution_completed", tool_name=name,
                  status="failure", error_type=type(error).__name__, error=str(error))
            raise


@mcp.tool()
def search_attractions(destination: str, number_of_days: int = 1,
                       interests: list[str] | None = None,
                       activity_type: str | None = None) -> dict:
    """Find attractions for a destination.

    Use for attraction and activity recommendations. Results are grounded in
    the configured data source; do not use this for restaurants or weather.
    """
    return _logged("search_attractions", _search_attractions, destination=destination,
                   number_of_days=number_of_days, interests=interests, activity_type=activity_type)


@mcp.tool()
def get_weather(destination: str, number_of_days: int = 1,
                travel_dates: list[str] | None = None) -> dict:
    """Get daily weather for a destination and requested dates.

    Use for weather questions or weather-aware planning. With travel_dates,
    provide one ordered YYYY-MM-DD date per requested day.
    """
    return _logged("get_weather", _get_weather, destination=destination,
                   number_of_days=number_of_days, travel_dates=travel_dates)


@mcp.tool()
def search_restaurants(destination: str, cuisine: str | None = None,
                       price_range: str | None = None, meal_type: str | None = None,
                       dietary_preferences: list[str] | None = None) -> dict:
    """Find restaurants and food options for a destination.

    Omit cuisine for broad requests such as good food or varied dining. Use a
    cuisine value only when the user names a specific cuisine.
    """
    return _logged("search_restaurants", _search_restaurants, destination=destination,
                   cuisine=cuisine, price_range=price_range, meal_type=meal_type,
                   dietary_preferences=dietary_preferences)


@mcp.tool()
def calculate_budget(destination: str, number_of_days: int, budget: float | None = None,
                     activities_cost: float = 0, meals_per_day: int = 3,
                     attractions: list[dict] | None = None,
                     restaurants: list[dict] | None = None,
                     travel_style: str = "moderate") -> dict:
    """Estimate trip costs and compare them with an optional budget.

    Use when the user states or asks for a budget. Pass returned attraction and
    restaurant results when available so activities and meals use grounded costs.
    Use travel_style for budget, moderate, or luxury assumptions when provider
    results do not include prices. Natural-language equivalents such as cheap,
    comfortable, or luxurious are also accepted. Costs are estimates, not
    booking quotes.
    """
    return _logged("calculate_budget", _calculate_budget, destination=destination,
                   number_of_days=number_of_days, budget=budget,
                   activities_cost=activities_cost, meals_per_day=meals_per_day,
                   attractions=attractions, restaurants=restaurants,
                   travel_style=travel_style)


@mcp.tool()
def create_itinerary(destination: str, number_of_days: int,
                     attractions: list[dict] | None = None,
                     restaurants: list[dict] | None = None,
                     weather: list[dict] | None = None,
                     budget: dict | None = None,
                     preferences: list[str] | None = None) -> dict:
    """Build a day-by-day schedule from gathered travel recommendations.

    Use for requests to plan, organize, schedule, or create a complete trip
    itinerary. Use only returned attraction, restaurant, weather, and budget
    data; never invent recommendations.
    """
    return _logged("create_itinerary", _create_itinerary, destination=destination,
                   number_of_days=number_of_days, attractions=attractions,
                   restaurants=restaurants, weather=weather, budget=budget,
                   preferences=preferences)


if __name__ == "__main__":
    configure_logging(settings.log_level)
    configure_tracing("travel-mcp-server")
    parser = argparse.ArgumentParser(description="Run the local travel MCP server")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"),
                        default="streamable-http")
    args = parser.parse_args()
    mcp.run(transport=args.transport)
