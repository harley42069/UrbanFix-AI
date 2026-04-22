"""
WebSocket Endpoint
WebSocket pour les mises à jour en temps réel des analyses
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Set
import json
import asyncio
from datetime import datetime

router = APIRouter()

# Gestionnaire de connexions WebSocket
class ConnectionManager:
    """Gestionnaire des connexions WebSocket"""
    
    def __init__(self):
        # Connexions actives par analysis_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Connexions globales (tous les événements)
        self.global_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, analysis_id: str = None):
        """
        Connecte un client WebSocket
        
        Args:
            websocket: WebSocket du client
            analysis_id: ID de l'analyse à suivre (None pour tous)
        """
        await websocket.accept()
        
        if analysis_id:
            if analysis_id not in self.active_connections:
                self.active_connections[analysis_id] = set()
            self.active_connections[analysis_id].add(websocket)
        else:
            self.global_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket, analysis_id: str = None):
        """
        Déconnecte un client WebSocket
        
        Args:
            websocket: WebSocket du client
            analysis_id: ID de l'analyse
        """
        if analysis_id:
            if analysis_id in self.active_connections:
                self.active_connections[analysis_id].discard(websocket)
                if not self.active_connections[analysis_id]:
                    del self.active_connections[analysis_id]
        else:
            self.global_connections.discard(websocket)
    
    async def send_message(self, message: dict, analysis_id: str):
        """
        Envoie un message à tous les clients d'une analyse
        
        Args:
            message: Message à envoyer
            analysis_id: ID de l'analyse
        """
        # Ajouter timestamp
        message["timestamp"] = datetime.now().isoformat()
        message_json = json.dumps(message)
        
        # Envoyer aux clients spécifiques à cette analyse
        if analysis_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[analysis_id]:
                try:
                    await connection.send_text(message_json)
                except Exception:
                    disconnected.add(connection)
            
            # Nettoyer les connexions déconnectées
            for conn in disconnected:
                self.active_connections[analysis_id].discard(conn)
        
        # Envoyer aux clients globaux
        disconnected_global = set()
        for connection in self.global_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected_global.add(connection)
        
        # Nettoyer les connexions globales déconnectées
        for conn in disconnected_global:
            self.global_connections.discard(conn)
    
    async def broadcast(self, message: dict):
        """
        Envoie un message à tous les clients
        
        Args:
            message: Message à envoyer
        """
        message["timestamp"] = datetime.now().isoformat()
        message_json = json.dumps(message)
        
        # Envoyer à tous les clients
        all_connections = set()
        for connections in self.active_connections.values():
            all_connections.update(connections)
        all_connections.update(self.global_connections)
        
        disconnected = set()
        for connection in all_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.add(connection)
        
        # Nettoyer les connexions déconnectées
        for conn in disconnected:
            for connections in self.active_connections.values():
                connections.discard(conn)
            self.global_connections.discard(conn)
    
    def get_connection_count(self, analysis_id: str = None) -> int:
        """
        Récupère le nombre de connexions
        
        Args:
            analysis_id: ID de l'analyse (None pour total)
            
        Returns:
            Nombre de connexions
        """
        if analysis_id:
            return len(self.active_connections.get(analysis_id, set()))
        else:
            total = len(self.global_connections)
            for connections in self.active_connections.values():
                total += len(connections)
            return total


# Instance globale du gestionnaire
manager = ConnectionManager()


@router.websocket("/analysis/{analysis_id}")
async def websocket_analysis_updates(websocket: WebSocket, analysis_id: str):
    """
    WebSocket pour suivre les mises à jour d'une analyse spécifique
    
    Args:
        websocket: WebSocket du client
        analysis_id: ID de l'analyse à suivre
    """
    await manager.connect(websocket, analysis_id)
    
    try:
        # Envoyer un message de confirmation
        await websocket.send_json({
            "type": "connected",
            "analysis_id": analysis_id,
            "message": f"Connecté aux mises à jour de l'analyse {analysis_id}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Envoyer le statut initial si disponible
        from app.api.endpoints.analysis import analysis_store
        if analysis_id in analysis_store:
            analysis = analysis_store[analysis_id]
            await websocket.send_json({
                "type": "status",
                "analysis_id": analysis_id,
                "status": analysis["status"],
                "progress": analysis.get("progress", 0),
                "current_step": analysis.get("current_step"),
                "message": analysis.get("message"),
                "timestamp": datetime.now().isoformat()
            })
        
        # Garder la connexion ouverte et écouter les messages du client
        while True:
            data = await websocket.receive_text()
            
            # Le client peut envoyer des commandes
            try:
                command = json.loads(data)
                
                if command.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif command.get("type") == "get_status":
                    if analysis_id in analysis_store:
                        analysis = analysis_store[analysis_id]
                        await websocket.send_json({
                            "type": "status",
                            "analysis_id": analysis_id,
                            "status": analysis["status"],
                            "progress": analysis.get("progress", 0),
                            "current_step": analysis.get("current_step"),
                            "message": analysis.get("message"),
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Analyse non trouvée",
                            "timestamp": datetime.now().isoformat()
                        })
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Format JSON invalide",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, analysis_id)
    except Exception as e:
        print(f"Erreur WebSocket: {e}")
        manager.disconnect(websocket, analysis_id)


@router.websocket("/global")
async def websocket_global_updates(websocket: WebSocket):
    """
    WebSocket pour suivre toutes les analyses
    
    Args:
        websocket: WebSocket du client
    """
    await manager.connect(websocket)
    
    try:
        # Message de confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Connecté aux mises à jour globales",
            "timestamp": datetime.now().isoformat()
        })
        
        # Garder la connexion ouverte
        while True:
            data = await websocket.receive_text()
            
            try:
                command = json.loads(data)
                
                if command.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif command.get("type") == "get_all_status":
                    from app.api.endpoints.analysis import analysis_store
                    analyses = [
                        {
                            "analysis_id": aid,
                            "status": a["status"],
                            "progress": a.get("progress", 0),
                            "current_step": a.get("current_step")
                        }
                        for aid, a in analysis_store.items()
                    ]
                    await websocket.send_json({
                        "type": "all_status",
                        "analyses": analyses,
                        "timestamp": datetime.now().isoformat()
                    })
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Format JSON invalide",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Erreur WebSocket: {e}")
        manager.disconnect(websocket)


async def notify_analysis_update(
    analysis_id: str,
    status: str,
    progress: float,
    current_step: str = None,
    message: str = None,
    results: dict = None
):
    """
    Envoie une notification de mise à jour d'analyse
    
    Args:
        analysis_id: ID de l'analyse
        status: Statut de l'analyse
        progress: Progression (0.0 à 1.0)
        current_step: Étape en cours
        message: Message descriptif
        results: Résultats (si terminé)
    """
    notification = {
        "type": "analysis_update",
        "analysis_id": analysis_id,
        "status": status,
        "progress": progress,
        "current_step": current_step,
        "message": message
    }
    
    if results and status == "completed":
        notification["results_available"] = True
    
    await manager.send_message(notification, analysis_id)


async def notify_error(analysis_id: str, error: str):
    """
    Envoie une notification d'erreur
    
    Args:
        analysis_id: ID de l'analyse
        error: Message d'erreur
    """
    notification = {
        "type": "error",
        "analysis_id": analysis_id,
        "message": error
    }
    
    await manager.send_message(notification, analysis_id)


async def notify_system_event(event_type: str, message: str, data: dict = None):
    """
    Envoie une notification système globale
    
    Args:
        event_type: Type d'événement
        message: Message
        data: Données additionnelles
    """
    notification = {
        "type": "system_event",
        "event_type": event_type,
        "message": message,
        "data": data or {}
    }
    
    await manager.broadcast(notification)


async def notify_signalement_updated(signalement_id: int, payload: dict):
    """
    Envoie un événement standard de progression pipeline d'un signalement.

    Event envoyé: ``signalement.updated``
    Channel ciblé: ``/ws/analysis/{signalement_id}``
    """
    notification = {
        "type": "signalement.updated",
        "signalement_id": signalement_id,
        **payload,
    }
    await manager.send_message(notification, str(signalement_id))


@router.get("/connections/count")
async def get_connections_count() -> dict:
    """
    Récupère le nombre de connexions WebSocket actives
    
    Returns:
        Nombre de connexions
    """
    return {
        "success": True,
        "data": {
            "total_connections": manager.get_connection_count(),
            "global_connections": len(manager.global_connections),
            "analysis_connections": {
                aid: len(conns)
                for aid, conns in manager.active_connections.items()
            }
        }
    }


# Exporter les fonctions de notification
__all__ = [
    "router",
    "manager",
    "notify_analysis_update",
    "notify_error",
    "notify_system_event",
    "notify_signalement_updated",
]
