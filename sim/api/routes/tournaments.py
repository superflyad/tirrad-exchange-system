"""Tournament routes for batch TES strategy/session execution."""

from __future__ import annotations

from fastapi import APIRouter, Request

from sim.api.models import TournamentChildrenResponse, TournamentConfig, TournamentReport, TournamentRun
from sim.api.services.tournament_service import TournamentService

router = APIRouter(tags=["tournaments"])


def _service(request: Request) -> TournamentService:
    return request.app.state.tournament_service


@router.post("/tournaments/run", response_model=TournamentRun)
def run_tournament(payload: TournamentConfig, request: Request) -> TournamentRun:
    return _service(request).run_tournament(payload)


@router.get("/tournaments", response_model=list[TournamentRun])
def list_tournaments(request: Request) -> list[TournamentRun]:
    return _service(request).list_tournaments()


@router.get("/tournaments/{tournament_id}", response_model=TournamentRun)
def get_tournament(tournament_id: str, request: Request) -> TournamentRun:
    return _service(request).get_tournament(tournament_id)


@router.get("/tournaments/{tournament_id}/report", response_model=TournamentReport)
def get_tournament_report(tournament_id: str, request: Request) -> TournamentReport:
    return _service(request).get_report(tournament_id)


@router.get("/tournaments/{tournament_id}/children", response_model=TournamentChildrenResponse)
def get_tournament_children(tournament_id: str, request: Request) -> TournamentChildrenResponse:
    return TournamentChildrenResponse(tournament_id=tournament_id, children=_service(request).get_children(tournament_id))


@router.post("/tournaments/{tournament_id}/cancel", response_model=TournamentRun)
def cancel_tournament(tournament_id: str, request: Request) -> TournamentRun:
    return _service(request).cancel_tournament(tournament_id)
