"""
Generate Grafana components
"""
from pathlib import Path
import kubernetes.client as k
import yaml
from . import util
from .datapath import DataPath


def generate(dst: Path, config: DataPath, stack_name: str):
    "Generate grafana manifests."
    output_dir = Path(dst, stack_name, "grafana")
    output_dir.mkdir(parents=True, exist_ok=True)
    client = k.ApiClient()
    name = config.get(f"stacks.{stack_name}.grafana.name", "grafana")
    port = config.get(f"stacks.{stack_name}.grafana.port", 3000)
    port_name = "ui"
    # deployment
    deployment = util.mk_deployment(
        name,
        port,
        port_name,
        config.get(f"stacks.{stack_name}.grafana.image", "grafana/grafana"),
        config[f"stacks.{stack_name}.grafana.resources.requests"],
        config[f"stacks.{stack_name}.grafana.resources.limits"],
    )
    yaml.safe_dump(
        client.sanitize_for_serialization(deployment),
        Path(output_dir / "deployment.yaml").open("w", encoding="utf-8"),
    )
    # hpa
    yaml.safe_dump(
        client.sanitize_for_serialization(
            util.mk_hpa(
                name,
                min_replicas=config[f"stacks.{stack_name}.grafana.minReplicas"],
                max_replicas=config[f"stacks.{stack_name}.grafana.maxReplicas"],
                scale_target_ref=k.V1CrossVersionObjectReference(
                    api_version=deployment.api_version,
                    kind=deployment.kind,
                    name=deployment.metadata.name,
                ),
            )
        ),
        Path(output_dir / "hpa.yaml").open("w", encoding="utf-8"),
    )
    # service
    yaml.safe_dump(
        client.sanitize_for_serialization(
            util.mk_service(
                name, port=port, port_name=port_name, service_type="NodePort"
            )
        ),
        Path(output_dir / "service.yaml").open("w", encoding="utf-8"),
    )
    # service-account
    yaml.safe_dump(
        client.sanitize_for_serialization(
            util.mk_service_account(name, automount_token=False)
        ),
        Path(output_dir / "service-account.yaml").open("w", encoding="utf-8"),
    )
