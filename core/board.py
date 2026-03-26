from typing import List, Optional, Dict
from pydantic import BaseModel

class BoardPosition(BaseModel):
    nodeId: str
    edgeId: Optional[str] = None
    edgeProgress: int = 0

BOARD_NODES = {
    "park": {"type": "start", "label": "Parque"},
    "branch-1": {"type": "branch", "label": "Cruce 1"},
    "branch-2a": {"type": "branch", "label": "Cruce 2A"},
    "branch-2b": {"type": "branch", "label": "Cruce 2B"},
    "branch-3": {"type": "branch", "label": "Cruce 3"},
    "branch-4a": {"type": "branch", "label": "Cruce 4A"},
    "branch-4b": {"type": "branch", "label": "Cruce 4B"},
    "branch-5": {"type": "branch", "label": "Cruce 5"},
    "hospital": {"type": "zone", "label": "Hospital"},
    "wifi": {"type": "zone", "label": "Wifi"},
    "home": {"type": "zone", "label": "Hogar"},
    "neighborhood": {"type": "zone", "label": "Barrio"},
    "school": {"type": "zone", "label": "Colegio"},
}

BOARD_EDGES = [
    {"id": "e-park-b1", "from": "park", "to": "branch-1", "distance": 5},
    {"id": "e-b1-b2a", "from": "branch-1", "to": "branch-2a", "distance": 3},
    {"id": "e-b1-b2b", "from": "branch-1", "to": "branch-2b", "distance": 4},
    {"id": "e-b2a-hospital", "from": "branch-2a", "to": "hospital", "distance": 9},
    {"id": "e-b2a-wifi", "from": "branch-2a", "to": "wifi", "distance": 9},
    {"id": "e-b2b-home", "from": "branch-2b", "to": "home", "distance": 5},
    {"id": "e-b2b-neigh", "from": "branch-2b", "to": "neighborhood", "distance": 7},
    {"id": "e-park-b3", "from": "park", "to": "branch-3", "distance": 5},
    {"id": "e-b3-b4a", "from": "branch-3", "to": "branch-4a", "distance": 10},
    {"id": "e-b3-b4b", "from": "branch-3", "to": "branch-4b", "distance": 6},
    {"id": "e-b4a-neigh", "from": "branch-4a", "to": "neighborhood", "distance": 7},
    {"id": "e-b4a-school", "from": "branch-4a", "to": "school", "distance": 11},
    {"id": "e-b4b-school", "from": "branch-4b", "to": "school", "distance": 9},
    {"id": "e-b4b-b5", "from": "branch-4b", "to": "branch-5", "distance": 7},
    {"id": "e-b5-park", "from": "branch-5", "to": "park", "distance": 10},
    {"id": "e-b5-hospital", "from": "branch-5", "to": "hospital", "distance": 7},
    
    # Reverse Edges for Bi-Directional traversing
    {"id": "e-b1-park", "from": "branch-1", "to": "park", "distance": 5},
    {"id": "e-b2a-b1", "from": "branch-2a", "to": "branch-1", "distance": 3},
    {"id": "e-b2b-b1", "from": "branch-2b", "to": "branch-1", "distance": 4},
    {"id": "e-hospital-b2a", "from": "hospital", "to": "branch-2a", "distance": 9},
    {"id": "e-wifi-b2a", "from": "wifi", "to": "branch-2a", "distance": 9},
    {"id": "e-home-b2b", "from": "home", "to": "branch-2b", "distance": 5},
    {"id": "e-neigh-b2b", "from": "neighborhood", "to": "branch-2b", "distance": 7},
    {"id": "e-b3-park", "from": "branch-3", "to": "park", "distance": 5},
    {"id": "e-b4a-b3", "from": "branch-4a", "to": "branch-3", "distance": 10},
    {"id": "e-b4b-b3", "from": "branch-4b", "to": "branch-3", "distance": 6},
    {"id": "e-neigh-b4a", "from": "neighborhood", "to": "branch-4a", "distance": 7},
    {"id": "e-school-b4a", "from": "school", "to": "branch-4a", "distance": 11},
    {"id": "e-school-b4b", "from": "school", "to": "branch-4b", "distance": 9},
    {"id": "e-b5-b4b", "from": "branch-5", "to": "branch-4b", "distance": 7},
    {"id": "e-park-b5", "from": "park", "to": "branch-5", "distance": 10},
    {"id": "e-hospital-b5", "from": "hospital", "to": "branch-5", "distance": 7},
]

def get_outgoing_edges(node_id: str) -> List[Dict]:
    return [e for e in BOARD_EDGES if e["from"] == node_id]

def get_edge(edge_id: str) -> Optional[Dict]:
    for e in BOARD_EDGES:
        if e["id"] == edge_id:
            return e
    return None

def move_player(current_pos: BoardPosition, steps: int, choice_edge_id: Optional[str] = None) -> Dict:
    """
    Simulates walking the graph step-by-step.
    Returns: {
        "newPosition": BoardPosition,
        "remainingSteps": int,
        "status": "moving" | "waiting_choice" | "zone_reached" | "finished",
        "options": List[str] (if waiting_choice),
        "zoneId": str (if zone_reached)
    }
    """
    pos = current_pos.copy()
    
    for _ in range(steps):
        # 1. If we are sitting on a node
        if pos.edgeId is None:
            outgoing = get_outgoing_edges(pos.nodeId)
            
            if len(outgoing) == 0:
                return {"newPosition": pos, "remainingSteps": 0, "status": "finished"}
            
            if len(outgoing) > 1 and choice_edge_id is None:
                # Need a choice from the player
                return {
                    "newPosition": pos, 
                    "remainingSteps": steps - _, 
                    "status": "waiting_choice",
                    "options": [e["id"] for e in outgoing]
                }
            
            # Select edge (either the only one or the chosen one)
            selected_edge = None
            if choice_edge_id:
                selected_edge = next((e for e in outgoing if e["id"] == choice_edge_id), None)
                # Clear choice for next steps in this loop
                choice_edge_id = None 
            else:
                selected_edge = outgoing[0]
            
            if not selected_edge:
                return {"newPosition": pos, "remainingSteps": 0, "status": "finished"}
                
            pos.edgeId = selected_edge["id"]
            pos.edgeProgress = 1
            
        # 2. If we are on an edge
        else:
            edge = get_edge(pos.edgeId)
            pos.edgeProgress += 1
            
            # Check if we reached the destination node
            if pos.edgeProgress >= edge["distance"]:
                pos.nodeId = edge["to"]
                pos.edgeId = None
                pos.edgeProgress = 0
                
                # Check if this node is a Zone
                node_info = BOARD_NODES.get(pos.nodeId)
                if node_info and node_info["type"] == "zone":
                    return {
                        "newPosition": pos, 
                        "remainingSteps": steps - _ - 1, 
                        "status": "zone_reached",
                        "zoneId": pos.nodeId
                    }
    
    # If we finished all steps
    return {"newPosition": pos, "remainingSteps": 0, "status": "finished"}
