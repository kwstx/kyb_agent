from .corporate import CorporateRegistryTool, CorporateDetailsTool
from .commercial import DunAndBradstreetTool, BureauVanDijkTool
from .sanctions import ComplyAdvantageTool, WorldCheckTool
from .search import WebSearchTool

def get_all_tools():
    """
    Returns a list of all unified KYB tools.
    """
    return [
        CorporateRegistryTool(),
        CorporateDetailsTool(),
        DunAndBradstreetTool(),
        BureauVanDijkTool(),
        ComplyAdvantageTool(),
        WorldCheckTool(),
        WebSearchTool()
    ]

__all__ = [
    "CorporateRegistryTool",
    "CorporateDetailsTool",
    "DunAndBradstreetTool",
    "BureauVanDijkTool",
    "ComplyAdvantageTool",
    "WorldCheckTool",
    "WebSearchTool",
    "get_all_tools"
]
