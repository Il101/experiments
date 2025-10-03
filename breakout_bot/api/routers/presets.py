"""
Presets management router
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
from datetime import datetime

from ...config.settings import Settings

router = APIRouter()

class PresetSummary(BaseModel):
    name: str
    description: str
    risk_per_trade: float
    max_positions: int
    strategy_type: str

class PresetConfig(BaseModel):
    name: str
    config: Dict[str, Any]

@router.get("/", response_model=List[PresetSummary])
async def get_presets():
    """Get list of available trading presets"""
    try:
        settings = Settings()
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "presets")
        
        presets = []
        for filename in os.listdir(config_dir):
            if filename.endswith(".json"):
                preset_name = filename[:-5]  # Remove .json extension
                try:
                    with open(os.path.join(config_dir, filename), 'r') as f:
                        preset_data = json.load(f)
                        
                    presets.append(PresetSummary(
                        name=preset_name,
                        description=preset_data.get("description", "No description"),
                        risk_per_trade=preset_data.get("risk", {}).get("risk_per_trade", 0.5),
                        max_positions=preset_data.get("risk", {}).get("max_concurrent_positions", 3),
                        strategy_type=preset_data.get("strategy_priority", "momentum")
                    ))
                except Exception as e:
                    continue  # Skip invalid preset files
        
        return presets
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load presets: {str(e)}"
        )

@router.get("/{preset_name}", response_model=PresetConfig)
async def get_preset(preset_name: str):
    """Get specific preset configuration"""
    try:
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "presets")
        preset_file = os.path.join(config_dir, f"{preset_name}.json")
        
        if not os.path.exists(preset_file):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preset '{preset_name}' not found"
            )
        
        with open(preset_file, 'r') as f:
            preset_data = json.load(f)
        
        return PresetConfig(
            name=preset_name,
            config=preset_data
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load preset: {str(e)}"
        )

@router.put("/{preset_name}")
async def update_preset(preset_name: str, config: Dict[str, Any]):
    """Update preset configuration"""
    try:
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "presets")
        preset_file = os.path.join(config_dir, f"{preset_name}.json")
        
        # Save updated configuration
        with open(preset_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return {
            "success": True,
            "message": f"Preset '{preset_name}' updated successfully",
            "timestamp": datetime.now().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preset: {str(e)}"
        )