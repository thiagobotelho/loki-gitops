"""Verifica limites da coleta OVN e preservação de application."""
from pathlib import Path
import re
import subprocess
import yaml

root = Path(__file__).resolve().parents[1]
for environment in ("desenvolvimento", "aceite", "producao"):
    objects = list(yaml.safe_load_all(subprocess.check_output(
        ["kubectl", "kustomize", str(root / "overlays" / environment)], text=True)))
    forwarder = next(obj for obj in objects if obj and obj["kind"] == "ClusterLogForwarder")
    spec = forwarder["spec"]
    app = next(p for p in spec["pipelines"] if p["name"] == "application-logs")
    assert app["inputRefs"] == ["application"]
    assert app["outputRefs"] == ["default-lokistack"]
    bindings = [obj for obj in objects if obj and obj["kind"] == "ClusterRoleBinding"
                and obj["metadata"]["name"].startswith("collector-crc-")]
    if environment != "desenvolvimento":
        assert not bindings
        assert not spec.get("inputs")
        continue
    assert len(bindings) == 2
    assert {obj["roleRef"]["name"] for obj in bindings} == {
        "collect-audit-logs", "cluster-logging-write-audit-logs"}
    assert spec["inputs"] == [{"name": "ovn-audit", "type": "audit",
                              "audit": {"sources": ["ovn"]}}]
    pipeline = next(p for p in spec["pipelines"] if p["name"] == "ovn-audit-mesh-lab")
    assert pipeline["inputRefs"] == ["ovn-audit"]
    assert pipeline["filterRefs"] == ["somente-mesh-lab"]
    condition = spec["filters"][0]["drop"][0]["test"][0]
    assert condition["field"] == ".message"
    pattern = condition["notMatches"]
    for accepted in ('name="NP:mesh-lab:Ingress", verdict=drop',
                     'name="NP:mesh-lab:httpbin-somente-sleep:Ingress:0", verdict=allow'):
        assert re.search(pattern, accepted)
    for rejected in ('name="NP:outro:Ingress", verdict=drop',
                     'name="NP:mesh-lab-outro:Ingress", verdict=allow',
                     'kube-apiserver audit event', ''):
        assert not re.search(pattern, rejected)
print("PASS: 3 perfis; application preservado; filtro OVN positivo e negativo")
