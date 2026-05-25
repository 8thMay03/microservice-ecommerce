"""
API routes for behavior prediction using trained RNN/LSTM/BiLSTM models.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
import torch
from pathlib import Path

from ..behavior_models import BehaviorPredictor
from ..behavior_preprocessing import BehaviorDataProcessor


router = APIRouter(prefix="/behavior", tags=["Behavior Prediction"])


# Global model instances (loaded on startup)
_predictors = {}
_processor = None


class BehaviorSequenceRequest(BaseModel):
    """Request for behavior prediction."""
    user_id: int
    actions: List[str]  # List of past actions: ['view', 'click', 'add_to_cart', ...]
    product_ids: Optional[List[int]] = None
    model_type: str = "bilstm"  # 'rnn', 'lstm', or 'bilstm'


class BehaviorPredictionResponse(BaseModel):
    """Response with predicted next action."""
    user_id: int
    predicted_action: str
    confidence: float
    model_used: str


class BehaviorTopKResponse(BaseModel):
    """Response with top-k predicted actions."""
    user_id: int
    predictions: List[dict]  # [{'action': 'purchase', 'probability': 0.75}, ...]
    model_used: str


class ModelInfo(BaseModel):
    """Information about loaded models."""
    available_models: List[str]
    default_model: str
    model_details: dict


def get_processor():
    """Dependency to get data processor."""
    global _processor
    if _processor is None:
        _processor = BehaviorDataProcessor(seq_length=10, max_seq_len=50)
    return _processor


def get_predictor(model_type: str = "bilstm") -> BehaviorPredictor:
    """
    Get or load a predictor for the specified model type.
    
    Args:
        model_type: Type of model ('rnn', 'lstm', 'bilstm')
        
    Returns:
        BehaviorPredictor instance
    """
    global _predictors
    
    model_type = model_type.lower()
    if model_type not in ['rnn', 'lstm', 'bilstm']:
        raise HTTPException(status_code=400, detail=f"Invalid model type: {model_type}")
    
    # Return cached predictor if available
    if model_type in _predictors:
        return _predictors[model_type]
    
    # Load model
    weights_dir = Path(__file__).parent.parent.parent / "weights" / "behavior_models"
    model_path = weights_dir / f"{model_type.upper()}_best_acc.pth"
    
    if not model_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Model weights not found: {model_path}. Please train the model first."
        )
    
    try:
        predictor = BehaviorPredictor(model_type=model_type, model_path=str(model_path))
        _predictors[model_type] = predictor
        return predictor
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")


@router.get("/models", response_model=ModelInfo)
async def get_model_info():
    """
    Get information about available behavior prediction models.
    """
    weights_dir = Path(__file__).parent.parent.parent / "weights" / "behavior_models"
    
    available_models = []
    model_details = {}
    
    for model_type in ['rnn', 'lstm', 'bilstm']:
        model_path = weights_dir / f"{model_type.upper()}_best_acc.pth"
        if model_path.exists():
            available_models.append(model_type)
            model_details[model_type] = {
                'path': str(model_path),
                'size_mb': model_path.stat().st_size / (1024 * 1024),
                'loaded': model_type in _predictors
            }
    
    if not available_models:
        raise HTTPException(
            status_code=404,
            detail="No trained models found. Please train models first using train_behavior_models.py"
        )
    
    return ModelInfo(
        available_models=available_models,
        default_model='bilstm' if 'bilstm' in available_models else available_models[0],
        model_details=model_details
    )


@router.post("/predict", response_model=BehaviorPredictionResponse)
async def predict_next_action(
    request: BehaviorSequenceRequest,
    processor: BehaviorDataProcessor = Depends(get_processor)
):
    """
    Predict the next action a user is likely to take based on their behavior history.
    
    Args:
        request: Behavior sequence with user actions
        
    Returns:
        Predicted next action with confidence score
    """
    if not request.actions:
        raise HTTPException(status_code=400, detail="Actions list cannot be empty")
    
    if len(request.actions) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 actions required for prediction"
        )
    
    try:
        # Get predictor
        predictor = get_predictor(request.model_type)
        
        # Encode sequence
        sequence = processor.encode_user_sequence(
            actions=request.actions,
            product_ids=request.product_ids
        )
        
        # Predict
        predicted_action, confidence = predictor.predict(sequence)
        
        return BehaviorPredictionResponse(
            user_id=request.user_id,
            predicted_action=predicted_action,
            confidence=confidence,
            model_used=request.model_type
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/predict/top-k", response_model=BehaviorTopKResponse)
async def predict_top_k_actions(
    request: BehaviorSequenceRequest,
    k: int = 3,
    processor: BehaviorDataProcessor = Depends(get_processor)
):
    """
    Predict top-k most likely next actions for a user.
    
    Args:
        request: Behavior sequence with user actions
        k: Number of top predictions to return (default: 3)
        
    Returns:
        Top-k predicted actions with probabilities
    """
    if not request.actions:
        raise HTTPException(status_code=400, detail="Actions list cannot be empty")
    
    if len(request.actions) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 actions required for prediction"
        )
    
    if k < 1 or k > 5:
        raise HTTPException(status_code=400, detail="k must be between 1 and 5")
    
    try:
        # Get predictor
        predictor = get_predictor(request.model_type)
        
        # Encode sequence
        sequence = processor.encode_user_sequence(
            actions=request.actions,
            product_ids=request.product_ids
        )
        
        # Predict top-k
        predictions = predictor.predict_top_k(sequence, k=k)
        
        # Format results
        formatted_predictions = [
            {'action': action, 'probability': float(prob)}
            for action, prob in predictions
        ]
        
        return BehaviorTopKResponse(
            user_id=request.user_id,
            predictions=formatted_predictions,
            model_used=request.model_type
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/analyze-sequence")
async def analyze_behavior_sequence(
    request: BehaviorSequenceRequest,
    processor: BehaviorDataProcessor = Depends(get_processor)
):
    """
    Analyze a behavior sequence and provide insights.
    
    Args:
        request: Behavior sequence with user actions
        
    Returns:
        Analysis of the behavior sequence
    """
    if not request.actions:
        raise HTTPException(status_code=400, detail="Actions list cannot be empty")
    
    try:
        # Count action types
        action_counts = {}
        for action in request.actions:
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Calculate engagement score (simple heuristic)
        engagement_weights = {
            'view': 1,
            'click': 2,
            'search': 2,
            'add_to_cart': 3,
            'purchase': 5
        }
        
        engagement_score = sum(
            engagement_weights.get(action.lower().replace(' ', '_'), 1)
            for action in request.actions
        )
        
        # Determine user intent
        if 'purchase' in request.actions:
            intent = 'high_intent_buyer'
        elif 'add_to_cart' in request.actions or 'add to cart' in request.actions:
            intent = 'medium_intent_browser'
        elif action_counts.get('view', 0) > len(request.actions) * 0.7:
            intent = 'low_intent_browser'
        else:
            intent = 'explorer'
        
        return {
            'user_id': request.user_id,
            'sequence_length': len(request.actions),
            'action_distribution': action_counts,
            'engagement_score': engagement_score,
            'user_intent': intent,
            'last_action': request.actions[-1],
            'unique_actions': len(set(request.actions))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/batch-predict")
async def batch_predict_actions(
    sequences: List[BehaviorSequenceRequest],
    processor: BehaviorDataProcessor = Depends(get_processor)
):
    """
    Predict next actions for multiple users in batch.
    
    Args:
        sequences: List of behavior sequences
        
    Returns:
        List of predictions for each user
    """
    if not sequences:
        raise HTTPException(status_code=400, detail="Sequences list cannot be empty")
    
    if len(sequences) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 sequences allowed per batch request"
        )
    
    results = []
    
    for seq_request in sequences:
        try:
            # Get predictor
            predictor = get_predictor(seq_request.model_type)
            
            # Encode and predict
            sequence = processor.encode_user_sequence(
                actions=seq_request.actions,
                product_ids=seq_request.product_ids
            )
            
            predicted_action, confidence = predictor.predict(sequence)
            
            results.append({
                'user_id': seq_request.user_id,
                'predicted_action': predicted_action,
                'confidence': float(confidence),
                'model_used': seq_request.model_type,
                'success': True
            })
            
        except Exception as e:
            results.append({
                'user_id': seq_request.user_id,
                'error': str(e),
                'success': False
            })
    
    return {
        'total_requests': len(sequences),
        'successful': sum(1 for r in results if r.get('success')),
        'failed': sum(1 for r in results if not r.get('success')),
        'results': results
    }


@router.get("/health")
async def health_check():
    """Health check endpoint for behavior prediction service."""
    return {
        'status': 'healthy',
        'service': 'behavior_prediction',
        'models_loaded': list(_predictors.keys()),
        'processor_initialized': _processor is not None
    }
