
import os
import json
import requests
import argparse
import getpass
from typing import List, Dict, Any, Optional, Tuple

# =========================
# CONFIGURAÇÃO (fixos)
# =========================
ORGANIZATION = "embraer-cloud"          # sua organização
PROJECT      = "eve-platform"           # seu projeto

# Lista de repositories (UUIDs) a varrer
REPOSITORY_IDS = [
    "ba111f91-8288-4e82-82ce-5c824047c7cb", #gateway-eve-front
    "e38fd85c-06d7-488d-ba27-63e2d7f38342", #platform-v2-eve-back
    "6137e1c9-6ffa-4655-8e93-90d824cc8c42", #platform-remote-eve-fron
    "95555be1-2428-40a1-9289-c75900f17cad", #eveconnect-eve-back
    "b3a52e2e-0327-4aaf-a374-1e8af7f81db8", #eveconnect-remote-eve-front
    "971b36b3-fb84-4eb0-a008-3986c7b1664c", #marketplace-eve-back
    "941b924d-1971-4ac2-81e4-7f7aa88b60d7" #marketplace-remote-eve-front
]

# Alvo (branch) das PRs
TARGET_REF   = "refs/heads/qas"
API_VERSION  = "7.1"

# Estratégia de merge e opções
MERGE_STRATEGY        = "noFastForward"   # "squash" | "noFastForward" | "rebase"
DELETE_SOURCE_BRANCH  = False
BYPASS_POLICY         = False             # cuidado: requer permissão para bypass
TIMEOUT               = 30


# =========================
# Helpers de parâmetros/segredos
# =========================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aprova e conclui PRs ativas cujo targetRefName corresponde ao alvo configurado."
    )
    parser.add_argument("--pat", help="Personal Access Token (PAT) do Azure DevOps")
    parser.add_argument("--reviewer-id", help="GUID do revisor que dará approve")
    return parser.parse_args()

def resolve_pat_and_reviewer_id(args: argparse.Namespace) -> Tuple[str, str]:
    """
    Resolve PAT e REVIEWER_ID com a seguinte prioridade:
      1) Parâmetros CLI (--pat, --reviewer-id)
      2) Variáveis de ambiente (AZURE_DEVOPS_PAT, REVIEWER_ID)
      3) Entrada interativa (getpass/input)
    """
    pat = args.pat or os.getenv("AZURE_DEVOPS_PAT")
    reviewer_id = args.reviewer_id or os.getenv("REVIEWER_ID")

    if not pat:
        # Entrada oculta para não vazar no terminal/histórico
        pat = getpass.getpass("Digite seu PAT (entrada oculta): ").strip()
        if not pat:
            raise RuntimeError("PAT não fornecido.")

    if not reviewer_id:
        reviewer_id = input("Digite o REVIEWER_ID (GUID do revisor): ").strip()
        if not reviewer_id:
            raise RuntimeError("REVIEWER_ID não fornecido.")

    return pat, reviewer_id


# =========================
# HTTP / Azure DevOps
# =========================
def make_session(pat: str) -> requests.Session:
    """Cria uma sessão HTTP com auth Basic (PAT)."""
    sess = requests.Session()
    # Usuário pode ser vazio; PAT é usado como senha
    sess.auth = requests.auth.HTTPBasicAuth('', pat)
    sess.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    return sess


def list_active_qas_prs(sess: requests.Session, org: str, project: str,
                        repo_id: str, target_ref: str,
                        api_version: str = API_VERSION,
                        top: int = 200) -> List[Dict[str, Any]]:
    """
    Retorna PRs ativas (status=active) com targetRefName=<target_ref> para um repo.
    Pagina com $top/$skip se necessário.
    """
    base = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/pullrequests"
    skip = 0
    results: List[Dict[str, Any]] = []

    while True:
        url = (f"{base}?searchCriteria.status=active"
               f"&searchCriteria.targetRefName={target_ref}"
               f"&api-version={api_version}"
               f"&$top={top}&$skip={skip}")
        resp = sess.get(url, timeout=TIMEOUT)
        if resp.status_code != 200:
            raise RuntimeError(
                f"[PR LIST] Falha repo={repo_id}, status={resp.status_code}, corpo={resp.text}"
            )
        payload = resp.json()
        values = payload.get("value", [])
        results.extend(values)

        if len(values) < top:
            break
        skip += top

    return results


def approve_pr(sess: requests.Session, org: str, project: str, repo_id: str,
               pr_id: int, reviewer_id: str,
               api_version: str = API_VERSION) -> Dict[str, Any]:
    """
    Aprova (vote=10) uma PR para o reviewer informado.
    """
    url = (f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}"
           f"/pullRequests/{pr_id}/reviewers/{reviewer_id}?api-version={api_version}")
    body = {"id": reviewer_id, "vote": 10}  # 10 = Approved
    resp = sess.put(url, data=json.dumps(body), timeout=TIMEOUT)
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"[APPROVE] Falha PR#{pr_id}, status={resp.status_code}, corpo={resp.text}"
        )
    return resp.json()


def complete_pr(sess: requests.Session, org: str, project: str, repo_id: str,
                pr_id: int, last_commit_id: Optional[str],
                merge_strategy: str = MERGE_STRATEGY,
                delete_source_branch: bool = DELETE_SOURCE_BRANCH,
                bypass_policy: bool = BYPASS_POLICY,
                api_version: str = API_VERSION) -> Dict[str, Any]:
    """
    Conclui (mergeia) uma PR com status=completed e opções de merge.
    Se last_commit_id for informado, usa-o para garantir idempotência.
    """
    url = (f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}"
           f"/pullRequests/{pr_id}?api-version={api_version}")
    body = {
        "status": "completed",
        "completionOptions": {
            "mergeStrategy": merge_strategy,
            "deleteSourceBranch": delete_source_branch,
            "bypassPolicy": bypass_policy
        }
    }
    # Só inclui lastMergeSourceCommit se houver valor
    if last_commit_id:
        body["lastMergeSourceCommit"] = {"commitId": last_commit_id}

    resp = sess.patch(url, data=json.dumps(body), timeout=TIMEOUT)
    if resp.status_code not in (200, 202):
        raise RuntimeError(
            f"[MERGE] Falha PR#{pr_id}, status={resp.status_code}, corpo={resp.text}"
        )
    return resp.json()


def process_repo(sess: requests.Session, repo_id: str, reviewer_id: str,
                 pr_ids_override: Optional[List[int]] = None) -> None:
    """
    Para um repo:
      - se pr_ids_override for fornecido, aprova/mergeia apenas esses IDs;
      - senão, descobre PRs ativas com target 'qas' e aprova/mergeia cada uma.
    """
    if pr_ids_override is None:
        prs = list_active_qas_prs(sess, ORGANIZATION, PROJECT, repo_id, TARGET_REF)
        if not prs:
            print(f"[INFO] Repo {repo_id}: nenhuma PR ativa para target '{TARGET_REF}'.")
            return
        # Mapeia PR -> lastMergeSourceCommit correspondente
        pr_items = [
            (
                p.get("pullRequestId"),
                (p.get("lastMergeSourceCommit") or {}).get("commitId")
            )
            for p in prs
            if p.get("pullRequestId") is not None
        ]
    else:
        # Quando há override, não temos o payload da PR para obter commit;
        # nesse caso, passa None para last_commit_id (Azure DevOps aceita).
        pr_items = [(pr_id, None) for pr_id in pr_ids_override]

    for pr_id, last_commit_id in pr_items:
        print(f"[RUN] Repo {repo_id} -> PR #{pr_id}: aprovando...")
        approve_payload = approve_pr(sess, ORGANIZATION, PROJECT, repo_id, pr_id, reviewer_id)
        print(f"       Approve OK (vote={approve_payload.get('vote')})")

        print(f"[RUN] Repo {repo_id} -> PR #{pr_id}: mergeando (last_commit_id={last_commit_id})...")
        merge_payload = complete_pr(
            sess, ORGANIZATION, PROJECT, repo_id, pr_id, last_commit_id
        )
        print(f"       Merge OK (status={merge_payload.get('status')}, mergeStatus={merge_payload.get('mergeStatus')})")


def main():
    args = parse_args()
    pat, reviewer_id = resolve_pat_and_reviewer_id(args)

    sess = make_session(pat)

    # MODO 1: Descobrir PRs ativas para TARGET_REF e processar todas
    for repo_id in REPOSITORY_IDS:
        try:
            process_repo(sess, repo_id, reviewer_id)
        except Exception as ex:
            print(f"[ERROR] Repo {repo_id}: {ex}")

    # MODO 2 (opcional): se você já tiver IDs de PR para cada repo,
    # chame 'process_repo(sess, repo_id, reviewer_id, pr_ids_override=[161197, ...])'


if __name__ == "__main__":
    main()
