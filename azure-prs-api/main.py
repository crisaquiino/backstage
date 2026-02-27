#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API REST para integração dos scripts Python com Backstage.io
Expõe endpoints para aprovar/mergear PRs e monitorar pipelines
"""

import os
import sys
import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Adiciona o diretório pai ao path para importar os scripts
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa funções dos scripts originais
from approve_merge_qas import (
    make_session,
    list_active_qas_prs,
    approve_pr,
    complete_pr,
    process_repo,
    ORGANIZATION,
    PROJECT,
    REPOSITORY_IDS,
    TARGET_REF,
    API_VERSION
)

# Importa módulo com hífen usando importlib
import importlib.util
watch_module_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   "watch_qas_pipelines_notify_teams-internal.py")
spec = importlib.util.spec_from_file_location("watch_qas_pipelines", watch_module_path)
watch_qas_pipelines = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch_qas_pipelines)

# Importa funções do módulo
make_watch_session = watch_qas_pipelines.make_session
get_running_or_queued_build = watch_qas_pipelines.get_running_or_queued_build
get_latest_completed_build = watch_qas_pipelines.get_latest_completed_build
get_build_by_id = watch_qas_pipelines.get_build_by_id
watch_repo_once_or_wait = watch_qas_pipelines.watch_repo_once_or_wait
QAS_BRANCH = watch_qas_pipelines.QAS_BRANCH
WATCH_REPOSITORY_IDS = watch_qas_pipelines.REPOSITORY_IDS
repo_alias = watch_qas_pipelines.repo_alias
repo_project = watch_qas_pipelines.repo_project

app = FastAPI(
    title="Azure DevOps Automation API",
    description="API para automação de PRs e pipelines do Azure DevOps",
    version="1.0.0"
)

# CORS para permitir requisições do Backstage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios do Backstage
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# Models
# =========================
class ApproveMergeRequest(BaseModel):
    pat: Optional[str] = None
    reviewer_id: Optional[str] = None
    repo_ids: Optional[List[str]] = None
    pr_ids: Optional[List[int]] = None


class WatchPipelineRequest(BaseModel):
    pat: Optional[str] = None
    teams_webhook_url: Optional[str] = None
    repo_ids: Optional[List[str]] = None
    once: bool = False
    timeout_min: int = 60
    poll_sec: int = 20


class BuildStatusResponse(BaseModel):
    repo_id: str
    repo_alias: str
    build_id: Optional[int] = None
    status: Optional[str] = None
    result: Optional[str] = None
    build_number: Optional[str] = None
    link: Optional[str] = None


# =========================
# Helpers
# =========================
def get_pat() -> str:
    """Obtém PAT das variáveis de ambiente ou retorna erro"""
    pat = os.getenv("AZURE_DEVOPS_PAT")
    if not pat:
        raise HTTPException(
            status_code=400,
            detail="AZURE_DEVOPS_PAT não configurado. Configure via variável de ambiente ou envie no request."
        )
    return pat


def get_reviewer_id() -> str:
    """Obtém REVIEWER_ID das variáveis de ambiente ou retorna erro"""
    reviewer_id = os.getenv("REVIEWER_ID")
    if not reviewer_id:
        raise HTTPException(
            status_code=400,
            detail="REVIEWER_ID não configurado. Configure via variável de ambiente ou envie no request."
        )
    return reviewer_id


# =========================
# Endpoints
# =========================
@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "Azure DevOps Automation API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check detalhado"""
    return {
        "status": "healthy",
        "pat_configured": bool(os.getenv("AZURE_DEVOPS_PAT")),
        "reviewer_id_configured": bool(os.getenv("REVIEWER_ID"))
    }


@app.post("/api/v1/prs/approve-merge")
async def approve_and_merge_prs(request: ApproveMergeRequest):
    """
    Aprova e faz merge de PRs ativas para a branch QAS.
    
    Se repo_ids não for fornecido, processa todos os repositórios configurados.
    Se pr_ids for fornecido, processa apenas essas PRs específicas.
    """
    try:
        pat = request.pat or get_pat()
        reviewer_id = request.reviewer_id or get_reviewer_id()
        
        sess = make_session(pat)
        repo_ids = request.repo_ids or REPOSITORY_IDS
        
        results = []
        errors = []
        
        for repo_id in repo_ids:
            try:
                if request.pr_ids:
                    # Modo específico: processa apenas as PRs informadas
                    process_repo(sess, repo_id, reviewer_id, pr_ids_override=request.pr_ids)
                    results.append({
                        "repo_id": repo_id,
                        "status": "success",
                        "message": f"Processadas {len(request.pr_ids)} PRs"
                    })
                else:
                    # Modo automático: descobre e processa todas as PRs ativas
                    process_repo(sess, repo_id, reviewer_id)
                    results.append({
                        "repo_id": repo_id,
                        "status": "success",
                        "message": "PRs processadas automaticamente"
                    })
            except Exception as ex:
                errors.append({
                    "repo_id": repo_id,
                    "error": str(ex)
                })
        
        return {
            "success": len(errors) == 0,
            "results": results,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/prs/active")
async def list_active_prs(repo_id: Optional[str] = None):
    """
    Lista PRs ativas para a branch QAS.
    
    Se repo_id não for fornecido, lista de todos os repositórios.
    """
    try:
        pat = get_pat()
        sess = make_session(pat)
        
        repo_ids = [repo_id] if repo_id else REPOSITORY_IDS
        all_prs = []
        
        for rid in repo_ids:
            try:
                prs = list_active_qas_prs(sess, ORGANIZATION, PROJECT, rid, TARGET_REF)
                for pr in prs:
                    pr["repo_id"] = rid
                all_prs.extend(prs)
            except Exception as ex:
                all_prs.append({
                    "repo_id": rid,
                    "error": str(ex)
                })
        
        return {
            "count": len([p for p in all_prs if "error" not in p]),
            "prs": all_prs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/pipelines/status")
async def get_pipeline_status(repo_id: Optional[str] = None):
    """
    Obtém status dos pipelines para a branch QAS.
    
    Retorna builds em execução ou o último build concluído.
    """
    try:
        pat = get_pat()
        sess = make_watch_session(pat)
        
        repo_ids = [repo_id] if repo_id else WATCH_REPOSITORY_IDS
        results = []
        
        for rid in repo_ids:
            try:
                project = repo_project(rid)
                alias = repo_alias(rid)
                
                # Tenta obter build em execução
                running = get_running_or_queued_build(sess, project, rid, QAS_BRANCH, None)
                
                if running:
                    build_id = running.get("id")
                    build = get_build_by_id(sess, project, build_id)
                    results.append({
                        "repo_id": rid,
                        "repo_alias": alias,
                        "build_id": build_id,
                        "status": build.get("status"),
                        "result": build.get("result"),
                        "build_number": build.get("buildNumber"),
                        "link": build.get("_links", {}).get("web", {}).get("href"),
                        "is_running": True
                    })
                else:
                    # Busca último build concluído
                    completed = get_latest_completed_build(sess, project, rid, QAS_BRANCH, None)
                    if completed:
                        results.append({
                            "repo_id": rid,
                            "repo_alias": alias,
                            "build_id": completed.get("id"),
                            "status": completed.get("status"),
                            "result": completed.get("result"),
                            "build_number": completed.get("buildNumber"),
                            "link": completed.get("_links", {}).get("web", {}).get("href"),
                            "is_running": False
                        })
                    else:
                        results.append({
                            "repo_id": rid,
                            "repo_alias": alias,
                            "status": "no_builds",
                            "message": "Nenhum build encontrado"
                        })
            except Exception as ex:
                results.append({
                    "repo_id": rid,
                    "error": str(ex)
                })
        
        return {
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/pipelines/watch")
async def watch_pipelines(request: WatchPipelineRequest, background_tasks: BackgroundTasks):
    """
    Inicia monitoramento de pipelines em background.
    
    Nota: Em produção, considere usar uma fila (Redis, RabbitMQ) ou workers.
    """
    try:
        pat = request.pat or get_pat()
        webhook = request.teams_webhook_url or os.getenv("TEAMS_WEBHOOK_URL")
        
        repo_ids = request.repo_ids or WATCH_REPOSITORY_IDS
        
        # Para execução em background, você pode usar Celery ou similar
        # Por enquanto, retorna instruções
        return {
            "message": "Watch iniciado",
            "repos": repo_ids,
            "note": "Para execução contínua, use o script diretamente ou implemente workers"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
