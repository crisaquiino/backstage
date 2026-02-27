
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import argparse
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# =========================
# CONFIG BÁSICA
# =========================
ORGANIZATION = "embraer-cloud"
DEFAULT_PROJECT = "eve-platform"
API_VERSION = "7.1"
TIMEOUT = 30

# Branch alvo
QAS_BRANCH = "refs/heads/qas"

# Repositórios a monitorar
REPOSITORY_IDS = [
    "048a7f00-2a9c-4a1a-b022-be6178bb5ecd", #internal-gateway-eve-front
    "d07e923e-2df8-44cc-95a5-81926fb48bfc", #internal-platform-eve-back
    "7ccb22f8-c068-4c6c-8236-24c6a6eef8fe", #internal-platform-remote-eve-front
    "5f4f06a5-3243-4e25-8d48-864878256fcd", #internal-eveconnect-eve-back
    "ccbf0746-fd1f-4929-96ef-99d44b897c68", #internal-eveconnect-remote-eve-front
    "f448b7ef-f14c-4b82-987e-4dc7573cffd9", #internal-marketplace-eve-back
    "1e6b18e9-1d37-4d57-876a-cb81b67f47b8" #internal-marketplace-remote-eve-front
]

# Apelidos (para facilitar leitura no Teams)
REPO_ALIASES: Dict[str, str] = {
    "048a7f00-2a9c-4a1a-b022-be6178bb5ecd": "internal-gateway-eve-front",
    "d07e923e-2df8-44cc-95a5-81926fb48bfc": "internal-platform-eve-back",
    "7ccb22f8-c068-4c6c-8236-24c6a6eef8fe": "internal-platform-remote-eve-front",
    "5f4f06a5-3243-4e25-8d48-864878256fcd": "internal-eveconnect-eve-back",
    "ccbf0746-fd1f-4929-96ef-99d44b897c68": "internal-eveconnect-remote-eve-front",
    "f448b7ef-f14c-4b82-987e-4dc7573cffd9": "internal-marketplace-eve-back",
    "1e6b18e9-1d37-4d57-876a-cb81b67f47b8": "internal-marketplace-remote-eve-front"
}

# Caso algum repo tenha pipeline em projeto diferente, mapeie aqui
REPO_PROJECTS: Dict[str, str] = {
    # "941b924d-1971-4ac2-81e4-7f7aa88b60d7": "outro-projeto"
}

# (Opcional) Fixar uma definição de build por repo, se houver múltiplos pipelines
REPO_DEFINITIONS: Dict[str, int] = {
    # "ba111f91-8288-4e82-82ce-5c824047c7cb": 123,  # Build Definition ID
}

# Polling
POLL_INTERVAL_SEC = 20
MAX_WAIT_SEC = 60 * 60  # 60 minutos

# =========================
# Utils
# =========================
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Vigia pipelines (branch qas) por repositório e notifica no Teams via Webhook."
    )
    p.add_argument("--pat", help="Personal Access Token (PAT) do Azure DevOps")
    p.add_argument("--teams-webhook-url", help="URL do Incoming Webhook do Teams")
    p.add_argument("--once", action="store_true",
                   help="Executa apenas uma checagem (não aguarda conclusão se não houver build em andamento).")
    p.add_argument("--timeout-min", type=int, default=60,
                   help="Tempo máximo para aguardar conclusão de builds em andamento (min). Default=60")
    p.add_argument("--poll-sec", type=int, default=20,
                   help="Intervalo entre polls (s). Default=20")
    p.add_argument("--repos", nargs="*", help="Filtra por uma ou mais repo_ids (se vazio, usa a lista padrão).")
    return p.parse_args()

def resolve_pat_and_webhook(args: argparse.Namespace) -> Tuple[str, Optional[str]]:
    pat = args.pat or os.getenv("AZURE_DEVOPS_PAT") or ""
    if not pat:
        raise RuntimeError("PAT não fornecido. Use --pat ou AZURE_DEVOPS_PAT.")
    webhook = args.teams_webhook_url or os.getenv("TEAMS_WEBHOOK_URL") or None
    return pat, webhook

def make_session(pat: str) -> requests.Session:
    sess = requests.Session()
    sys_token = os.getenv("SYSTEM_ACCESSTOKEN")
    token = sys_token or pat
    sess.auth = requests.auth.HTTPBasicAuth('', token)
    sess.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "qas-pipeline-watcher/1.0"
    })
    return sess

def sanity_check_permissions(sess: requests.Session) -> None:
    url_conn = f"https://dev.azure.com/{ORGANIZATION}/_apis/connectionData?api-version={API_VERSION}"
    r = sess.get(url_conn, timeout=TIMEOUT)
    if r.status_code == 401:
        raise RuntimeError("401 na conexão: verifique PAT/token. Pode estar inválido/expirado.")
    # Smoke test Builds no projeto default
    url_builds = f"https://dev.azure.com/{ORGANIZATION}/{DEFAULT_PROJECT}/_apis/build/builds"
    r2 = sess.get(url_builds, params={"$top": "1", "api-version": API_VERSION}, timeout=TIMEOUT)
    if r2.status_code == 401:
        raise RuntimeError("401 em Builds: habilite escopo 'Build: Read' no PAT e permissão no projeto/pipeline.")

def repo_project(repo_id: str) -> str:
    return REPO_PROJECTS.get(repo_id, DEFAULT_PROJECT)

def repo_alias(repo_id: str) -> str:
    return REPO_ALIASES.get(repo_id, repo_id)

def definition_for_repo(repo_id: str) -> Optional[int]:
    return REPO_DEFINITIONS.get(repo_id)

def fmt_result_emoji(result: Optional[str]) -> str:
    if not result:
        return "❔"
    r = result.lower()
    if r == "succeeded":
        return "✅"
    if r == "partiallysucceeded":
        return "🟡"
    if r == "failed":
        return "❌"
    if r == "canceled":
        return "⚠️"
    return "❔"

def iso_to_dt(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return None

def build_duration_text(b: Dict[str, Any]) -> str:
    dt_start = iso_to_dt(b.get("startTime"))
    dt_end = iso_to_dt(b.get("finishTime"))
    if dt_start and dt_end:
        delta = dt_end - dt_start
        total = int(delta.total_seconds())
        return f"{total//60}m{total%60}s"
    return "n/d"

# =========================
# Azure DevOps Builds API
# =========================
def get_running_or_queued_build(
    sess: requests.Session, project: str, repo_id: str, branch_ref: str, definition_id: Optional[int]
) -> Optional[Dict[str, Any]]:
    base = f"https://dev.azure.com/{ORGANIZATION}/{project}/_apis/build/builds"
    params = {
        "repositoryId": repo_id,
        "repositoryType": "TfsGit",
        "branchName": branch_ref,
        "queryOrder": "queueTimeDescending",
        "$top": "3",
        "api-version": API_VERSION
    }
    if definition_id:
        params["definitions"] = str(definition_id)

    r = sess.get(base, params=params, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"[RUNNING] Falha repo={repo_id}, proj={project}, status={r.status_code}, corpo={r.text}")

    for b in r.json().get("value", []):
        status = (b.get("status") or "").lower()
        if status != "completed":
            return b
    return None

def get_latest_completed_build(
    sess: requests.Session, project: str, repo_id: str, branch_ref: str, definition_id: Optional[int]
) -> Optional[Dict[str, Any]]:
    base = f"https://dev.azure.com/{ORGANIZATION}/{project}/_apis/build/builds"
    params = {
        "repositoryId": repo_id,
        "repositoryType": "TfsGit",
        "branchName": branch_ref,
        "statusFilter": "completed",
        "queryOrder": "finishTimeDescending",
        "$top": "1",
        "api-version": API_VERSION
    }
    if definition_id:
        params["definitions"] = str(definition_id)

    r = sess.get(base, params=params, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"[COMPLETED] Falha repo={repo_id}, proj={project}, status={r.status_code}, corpo={r.text}")
    values = r.json().get("value", [])
    return values[0] if values else None

def get_build_by_id(sess: requests.Session, project: str, build_id: int) -> Dict[str, Any]:
    url = f"https://dev.azure.com/{ORGANIZATION}/{project}/_apis/build/builds/{build_id}"
    r = sess.get(url, params={"api-version": API_VERSION}, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"[BUILD GET] Falha build={build_id}, status={r.status_code}, corpo={r.text}")
    return r.json()

# =========================
# Teams Webhook
# =========================
def send_teams(webhook_url: str, title: str, lines: List[str], color: str = "0078D7") -> None:
    text = "\n".join([l for l in lines if l is not None and l != ""])
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": title,
        "themeColor": color,
        "title": title,
        "text": text
    }
    r = requests.post(webhook_url, data=json.dumps(payload),
                      headers={"Content-Type": "application/json"}, timeout=TIMEOUT, verify=False)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"[TEAMS] Falha ao enviar mensagem (status={r.status_code}, corpo={r.text})")

def color_for_result(result: Optional[str]) -> str:
    if not result:
        return "767676"  # cinza
    r = result.lower()
    if r == "succeeded":
        return "2EB886"  # verde
    if r == "partiallysucceeded":
        return "FFB900"  # amarelo
    if r == "failed":
        return "E81123"  # vermelho
    if r == "canceled":
        return "8A8886"  # cinza
    return "0078D7"      # azul

# =========================
# Lógica principal
# =========================
def watch_repo_once_or_wait(
    sess: requests.Session,
    repo_id: str,
    branch_ref: str,
    webhook: Optional[str],
    once: bool,
    poll_interval_sec: int,
    max_wait_sec: int
) -> None:
    alias = repo_alias(repo_id)
    project = repo_project(repo_id)
    definition_id = definition_for_repo(repo_id)

    print(f"[INFO] Repo={alias} (proj={project}) — observando branch {branch_ref}")

    try:
        running = get_running_or_queued_build(sess, project, repo_id, branch_ref, definition_id)
    except Exception as ex:
        print(f"[WARN] {alias}: erro ao buscar builds em execução: {ex}")
        running = None

    if running:
        build_id = running.get("id")
        print(f"[INFO] {alias}: build em andamento id={build_id}. Aguardando conclusão...")
        start = time.time()
        while True:
            if time.time() - start > max_wait_sec:
                print(f"[WARN] {alias}: timeout aguardando build {build_id}")
                if webhook:
                    send_teams(
                        webhook,
                        f"[QAS] Timeout aguardando pipeline — {alias}",
                        [
                            f"Repositório: **{alias}**",
                            f"Build em andamento: **{build_id}**",
                            f"Status: ⏳ Timeout após {max_wait_sec//60} min."
                        ],
                        color="767676"
                    )
                return
            b = get_build_by_id(sess, project, build_id)
            if (b.get("status") or "").lower() == "completed":
                result = b.get("result")
                emoji = fmt_result_emoji(result)
                link = b.get("_links", {}).get("web", {}).get("href", "")
                num = b.get("buildNumber", str(build_id))
                dur = build_duration_text(b)
                print(f"[INFO] {alias}: build {build_id} concluído: {result}")
                if webhook:
                    send_teams(
                        webhook,
                        f"[QAS] Pipeline finalizado — {alias} {emoji}",
                        [
                            f"Repositório: **{alias}**",
                            f"Build: **{num}** (id={build_id})",
                            f"Resultado: **{result or 'desconhecido'}** {emoji}",
                            f"Duração: {dur}",
                            link
                        ],
                        color=color_for_result(result)
                    )
                return
            time.sleep(poll_interval_sec)

    # Não há build em andamento
    if once:
        try:
            last_completed = get_latest_completed_build(sess, project, repo_id, branch_ref, definition_id)
        except Exception as ex:
            print(f"[WARN] {alias}: erro ao buscar último completed: {ex}")
            last_completed = None

        if last_completed and webhook:
            result = last_completed.get("result")
            emoji = fmt_result_emoji(result)
            link = last_completed.get("_links", {}).get("web", {}).get("href", "")
            build_id = last_completed.get("id")
            num = last_completed.get("buildNumber", str(build_id))
            dur = build_duration_text(last_completed)
            send_teams(
                webhook,
                f"[QAS] Último pipeline (completed) — {alias} {emoji}",
                [
                    f"Repositório: **{alias}**",
                    f"Build: **{num}** (id={build_id})",
                    f"Resultado: **{result or 'desconhecido'}** {emoji}",
                    f"Duração: {dur}",
                    link
                ],
                color=color_for_result(result)
            )
        else:
            print(f"[INFO] {alias}: nenhum build em execução. Use sem --once para aguardar novos builds.")
        return

    # Esperar até surgir um build (modo watch)
    print(f"[INFO] {alias}: aguardando surgir build em qas...")
    start = time.time()
    while True:
        if time.time() - start > max_wait_sec:
            print(f"[WARN] {alias}: timeout aguardando início de build.")
            if webhook:
                send_teams(
                    webhook,
                    f"[QAS] Nenhum pipeline detectado no período — {alias}",
                    [
                        f"Repositório: **{alias}**",
                        f"Status: ⏳ Nenhum build iniciou em {max_wait_sec//60} min."
                    ],
                    color="767676"
                )
            return
        running = get_running_or_queued_build(sess, project, repo_id, branch_ref, definition_id)
        if running:
            # agora acompanha até terminar
            build_id = running.get("id")
            print(f"[INFO] {alias}: build iniciado id={build_id}. Aguardando conclusão...")
            while True:
                b = get_build_by_id(sess, project, build_id)
                if (b.get("status") or "").lower() == "completed":
                    result = b.get("result")
                    emoji = fmt_result_emoji(result)
                    link = b.get("_links", {}).get("web", {}).get("href", "")
                    num = b.get("buildNumber", str(build_id))
                    dur = build_duration_text(b)
                    print(f"[INFO] {alias}: build {build_id} concluído: {result}")
                    if webhook:
                        send_teams(
                            webhook,
                            f"[QAS] Pipeline finalizado — {alias} {emoji}",
                            [
                                f"Repositório: **{alias}**",
                                f"Build: **{num}** (id={build_id})",
                                f"Resultado: **{result or 'desconhecido'}** {emoji}",
                                f"Duração: {dur}",
                                link
                            ],
                            color=color_for_result(result)
                        )
                    return
                time.sleep(POLL_INTERVAL_SEC)
        time.sleep(POLL_INTERVAL_SEC)

def main():
    args = parse_args()
    pat, webhook = resolve_pat_and_webhook(args)

    # overrides
    global MAX_WAIT_SEC, POLL_INTERVAL_SEC
    MAX_WAIT_SEC = max(60, args.timeout_min * 60)
    POLL_INTERVAL_SEC = max(5, args.poll_sec)

    repos = args.repos if args.repos else REPOSITORY_IDS

    sess = make_session(pat)
    try:
        sanity_check_permissions(sess)
    except Exception as ex:
        print(f"[ERROR] Sanity check: {ex}")
        return

    for repo_id in repos:
        try:
            watch_repo_once_or_wait(
                sess=sess,
                repo_id=repo_id,
                branch_ref=QAS_BRANCH,
                webhook=webhook,
                once=args.once,
                poll_interval_sec=POLL_INTERVAL_SEC,
                max_wait_sec=MAX_WAIT_SEC
            )
        except Exception as ex:
            alias = repo_alias(repo_id)
            print(f"[ERROR] {alias}: {ex}")

if __name__ == "__main__":
    main()
