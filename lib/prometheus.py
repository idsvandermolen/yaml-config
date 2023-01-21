"""
Generate Prometheus components
"""
from pathlib import Path
import kubernetes.client as k
from ruamel.yaml import YAML
from datapath import DataPath
from . import util


def generate(dst: Path, components: Path, config: DataPath, stack_name: str):
    "Generate prometheus manifests."
    output_dir = Path(dst, stack_name, "prometheus")
    output_dir.mkdir(parents=True, exist_ok=True)
    client = k.ApiClient()
    name = config.get(f"stacks.{stack_name}.prometheus.name", "prometheus")
    port = config.get(f"stacks.{stack_name}.prometheus.port", 9090)
    port_name = "api"
    # deployment
    image = config.get(
        f"stacks.{stack_name}.prometheus.image", "prom/prometheus:latest"
    )
    requests = config.get(
        f"stacks.{stack_name}.prometheus.resources.requests",
        {"cpu": "1", "memory": "1G"},
    )
    limits = config.get(
        f"stacks.{stack_name}.prometheus.resources.limits",
        {"cpu": "1", "memory": "1G"},
    )
    deployment = util.mk_deployment(
        name,
        [
            k.V1Container(
                name=name,
                image=image,
                ports=[
                    k.V1ContainerPort(
                        name=port_name,
                        container_port=port,
                    )
                ],
                resources=k.V1ResourceRequirements(
                    requests=requests,
                    limits=limits,
                ),
            )
        ],
    )
    yaml = YAML()
    yaml.dump(
        client.sanitize_for_serialization(deployment),
        Path(output_dir / "deployment.yaml").open("w", encoding="utf-8"),
    )
    # hpa
    yaml.dump(
        client.sanitize_for_serialization(
            util.mk_hpa(
                name,
                min_replicas=config.get(
                    f"stacks.{stack_name}.prometheus.minReplicas", 1
                ),
                max_replicas=config.get(
                    f"stacks.{stack_name}.prometheus.maxReplicas", 1
                ),
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
    yaml.dump(
        client.sanitize_for_serialization(
            util.mk_service(name, port=port, port_name=port_name)
        ),
        Path(output_dir / "service.yaml").open("w", encoding="utf-8"),
    )
    # service-account
    yaml.dump(
        client.sanitize_for_serialization(
            util.mk_service_account(name, automount_token=False)
        ),
        Path(output_dir / "service-account.yaml").open("w", encoding="utf-8"),
    )
    # ArgoCD app
    app = DataPath(
        yaml.load(Path(components, "argocd", "prometheus.yaml").open(encoding="utf-8"))
    )
    app["spec.source.path"] = str(output_dir)
    yaml.dump(
        app.data, Path(output_dir, "application.yaml").open("w", encoding="utf-8")
    )
