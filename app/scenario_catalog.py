"""Pre-seeded cloud/network/K8s/Linux troubleshooting scenarios: a
situation (with realistic given logs/config/command output), an ask, and a
key_points checklist Claude grades against (see get_scenario_review) to
keep free-text grading consistent across scenarios."""
import json

from sqlmodel import Session, select

from app.models import ScenarioProblem

SCENARIO_CATALOG = [
    # ------------------------------------------------------------ kubernetes
    {
        "title": "CrashLoopBackOff on a slow-starting service",
        "area": "kubernetes",
        "difficulty": "Medium",
        "situation": (
            "A Deployment's pods keep restarting. `kubectl get pods` shows "
            "STATUS CrashLoopBackOff. The app is known to take about 25-30 "
            "seconds to finish loading its config and start listening.\n\n"
            "Deployment spec (relevant part):\n"
            "```yaml\n"
            "    livenessProbe:\n"
            "      httpGet:\n"
            "        path: /healthz\n"
            "        port: 8080\n"
            "      initialDelaySeconds: 0\n"
            "      periodSeconds: 5\n"
            "      failureThreshold: 3\n"
            "```\n\n"
            "`kubectl describe pod` events:\n"
            "```\n"
            "Warning  Unhealthy  Liveness probe failed: Get \"http://10.1.2.3:8080/healthz\": "
            "dial tcp 10.1.2.3:8080: connect: connection refused\n"
            "Normal   Killing    Container app failed liveness probe, will be restarted\n"
            "```"
        ),
        "ask": "Diagnose the root cause and propose a fix.",
        "key_points": [
            "liveness probe starts checking immediately (initialDelaySeconds: 0), before the "
            "app has finished its ~30s startup",
            "with periodSeconds 5 and failureThreshold 3, the probe kills the container about "
            "15s in, before it can ever come up healthy -- an endless restart loop",
            "fix: raise initialDelaySeconds past the real startup time, or better, add a "
            "startupProbe so liveness only kicks in once startup succeeds",
        ],
    },
    {
        "title": "Service has no endpoints",
        "area": "kubernetes",
        "difficulty": "Easy",
        "situation": (
            "Requests to a Service time out. `kubectl get endpoints web-svc` shows no "
            "addresses. The pods themselves are Running and healthy.\n\n"
            "Service:\n"
            "```yaml\n"
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: web-svc\nspec:\n"
            "  selector:\n    app: web\n  ports:\n    - port: 80\n      targetPort: 8080\n"
            "```\n\n"
            "Deployment pod template labels:\n"
            "```yaml\n"
            "  template:\n    metadata:\n      labels:\n        app: webapp\n"
            "```"
        ),
        "ask": "Diagnose the root cause and propose a fix.",
        "key_points": [
            "the Service selector (app: web) doesn't match the pod template's labels "
            "(app: webapp), so the Service has nothing to route to",
            "empty endpoints is the direct symptom of a selector/label mismatch, not a "
            "networking or DNS problem",
            "fix: make the selector and pod labels match, either change the Service selector "
            "to app: webapp or the pod labels to app: web",
        ],
    },
    {
        "title": "ImagePullBackOff on deploy",
        "area": "kubernetes",
        "difficulty": "Easy",
        "situation": (
            "A new Deployment's pods sit in ImagePullBackOff. The image lives in a private "
            "registry.\n\n"
            "`kubectl describe pod` events:\n"
            "```\n"
            "Warning  Failed  Failed to pull image \"registry.example.com/app:1.4.2\": "
            "unauthorized: authentication required\n"
            "```\n\n"
            "Pod spec (relevant part):\n"
            "```yaml\n"
            "spec:\n  containers:\n    - name: app\n      image: registry.example.com/app:1.4.2\n"
            "```"
        ),
        "ask": "Diagnose the root cause and propose a fix.",
        "key_points": [
            "the pod spec has no imagePullSecrets, so kubelet has no credentials for the "
            "private registry",
            "'unauthorized: authentication required' points specifically at missing/invalid "
            "registry auth, not a bad tag or a nonexistent image",
            "fix: create a docker-registry Secret with valid credentials and reference it via "
            "imagePullSecrets on the pod spec (or the namespace's default service account)",
        ],
    },
    # ------------------------------------------------------------- networking
    {
        "title": "Cluster IP works, DNS name doesn't",
        "area": "networking",
        "difficulty": "Medium",
        "situation": (
            "From a pod in namespace `frontend`, `curl 10.96.34.12:80` (the Service's cluster "
            "IP) succeeds, but `curl http://backend-svc:80` fails with "
            "\"could not resolve host: backend-svc\". The target Service, `backend-svc`, "
            "actually lives in namespace `backend`."
        ),
        "ask": "Diagnose why the DNS name fails while the IP works, and propose a fix.",
        "key_points": [
            "the IP working rules out network policy/connectivity as the problem, this is a "
            "DNS resolution issue specifically",
            "a bare Service name only resolves within its own namespace's default search "
            "domain; from a different namespace it needs the namespace qualified, e.g. "
            "backend-svc.backend or the full backend-svc.backend.svc.cluster.local",
            "fix: use the namespace-qualified name (backend-svc.backend) rather than the bare "
            "name from frontend's pods",
        ],
    },
    {
        "title": "App can't reach the database",
        "area": "networking",
        "difficulty": "Medium",
        "situation": (
            "An app on EC2 (security group `sg-app`) times out connecting to RDS Postgres "
            "(security group `sg-db`) on port 5432. The app can reach other services fine.\n\n"
            "sg-db inbound rules:\n"
            "```\n"
            "Type        Protocol  Port   Source\n"
            "SSH         TCP       22     10.0.0.0/16\n"
            "HTTPS       TCP       443    10.0.0.0/16\n"
            "```"
        ),
        "ask": "Diagnose the root cause and propose a fix.",
        "key_points": [
            "sg-db's inbound rules have no entry for port 5432 at all, so Postgres traffic is "
            "dropped regardless of source",
            "the fix is a security group rule problem, not a route table, NACL, or app-config "
            "problem (rule out those first, but the given rules already show the gap)",
            "fix: add an inbound rule on sg-db allowing TCP 5432 from sg-app (or the app's "
            "subnet CIDR)",
        ],
    },
    {
        "title": "One-way connectivity across VPC peering",
        "area": "networking",
        "difficulty": "Hard",
        "situation": (
            "Two VPCs are peered: VPC A (10.0.0.0/16) and VPC B (10.1.0.0/16). A host in VPC A "
            "can successfully ping a host in VPC B, but the VPC B host cannot ping back to VPC "
            "A. Security groups on both hosts allow all ICMP from the peer CIDR.\n\n"
            "VPC A route table: has a route for 10.1.0.0/16 -> pcx-0123abc (the peering "
            "connection).\n"
            "VPC B route table: has no route for 10.0.0.0/16."
        ),
        "ask": "Diagnose the root cause and propose a fix.",
        "key_points": [
            "VPC peering routes aren't automatic in each direction, each VPC's route table "
            "needs its own explicit route pointing back through the peering connection",
            "VPC B's route table is missing the 10.0.0.0/16 -> pcx-0123abc route, so return "
            "traffic (or B-initiated traffic to A) has nowhere to go",
            "fix: add a route on VPC B's route table for 10.0.0.0/16 via the peering connection",
        ],
    },
    # ------------------------------------------------------------------ linux
    {
        "title": "systemd service can't write its logs",
        "area": "linux",
        "difficulty": "Easy",
        "situation": (
            "A systemd-managed app fails to start. `journalctl -u app` shows "
            "\"PermissionError: [Errno 13] Permission denied: '/var/log/app/app.log'\".\n\n"
            "Unit file (relevant part):\n"
            "```ini\n[Service]\nUser=appuser\nExecStart=/usr/local/bin/app\n```\n\n"
            "`ls -la /var/log/app`:\n"
            "```\ndrwxr-xr-x 2 root root 4096 Jan  5 10:00 .\n```"
        ),
        "ask": "Diagnose the root cause and propose a fix.",
        "key_points": [
            "the service runs as appuser (User=appuser), but /var/log/app is owned by root "
            "with mode 755 (no write for group/other), so appuser can't create the log file",
            "this is a straightforward ownership/permissions mismatch, not a SELinux or "
            "systemd sandboxing issue given no such directives are shown",
            "fix: chown the log directory to appuser (or a shared group appuser belongs to) "
            "so the service user can write to it",
        ],
    },
    {
        "title": "Service fails on boot, works with manual start",
        "area": "linux",
        "difficulty": "Medium",
        "situation": (
            "A systemd service fails after every reboot but starts fine with "
            "`systemctl start app` afterward. `journalctl -u app -b` on boot shows: "
            "\"bind: Cannot assign requested address\" for the app's configured listen IP.\n\n"
            "Unit file:\n"
            "```ini\n[Unit]\nDescription=app\n\n[Service]\nExecStart=/usr/local/bin/app\n"
            "Restart=no\n\n[Install]\nWantedBy=multi-user.target\n```"
        ),
        "ask": "Diagnose the root cause and propose a fix.",
        "key_points": [
            "the unit has no ordering/dependency on the network being up (no "
            "After=network-online.target / Wants=network-online.target), so systemd can start "
            "it before the interface has its address configured",
            "it works manually because by the time you log in and run it, networking has "
            "already finished initializing",
            "fix: add Wants=network-online.target and After=network-online.target to [Unit] "
            "(and ensure the network-online.target provider, e.g. systemd-networkd-wait-online, "
            "is enabled)",
        ],
    },
    {
        "title": "\"No space left on device\" with free disk space",
        "area": "linux",
        "difficulty": "Medium",
        "situation": (
            "An app errors with \"OSError: [Errno 28] No space left on device\" when writing a "
            "new file, but `df -h` shows plenty of free space:\n"
            "```\nFilesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/sda1        50G   12G   36G  26% /\n```"
        ),
        "ask": "Diagnose the root cause and propose a fix.",
        "key_points": [
            "free space in df -h doesn't rule out running out of inodes, a filesystem can "
            "have plenty of bytes free but zero inodes left if something created huge numbers "
            "of tiny files",
            "the next step is checking df -i for inode usage, not trusting df -h alone",
            "fix: find and clean up whatever's generating excessive small files (e.g. a "
            "runaway process writing per-request temp/session files), then address the root "
            "cause so it doesn't recur",
        ],
    },
    # --------------------------------------------------------------- security
    {
        "title": "S3 bucket exposing files publicly",
        "area": "security",
        "difficulty": "Medium",
        "situation": (
            "A security scan flags an S3 bucket as publicly readable, and sensitive files were "
            "confirmed accessible via a direct URL with no authentication.\n\n"
            "Bucket policy:\n"
            "```json\n"
            "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n"
            "      \"Effect\": \"Allow\",\n      \"Principal\": \"*\",\n"
            "      \"Action\": \"s3:GetObject\",\n"
            "      \"Resource\": \"arn:aws:s3:::company-data/*\"\n    }\n  ]\n}\n```"
        ),
        "ask": "Diagnose the root cause and propose a fix.",
        "key_points": [
            "the bucket policy grants s3:GetObject to Principal \"*\", meaning anyone on the "
            "internet, unauthenticated, that's the direct cause of the exposure",
            "this is a bucket-policy misconfiguration, not an IAM user/role problem",
            "fix: remove the public Allow statement (scope Principal to specific accounts/"
            "roles that need it), and enable S3 Block Public Access on the bucket/account as "
            "defense in depth",
        ],
    },
    {
        "title": "SSH brute-force exposure",
        "area": "security",
        "difficulty": "Easy",
        "situation": (
            "`/var/log/auth.log` shows hundreds of failed root login attempts per hour from "
            "many different IPs:\n"
            "```\nFailed password for root from 203.0.113.5 port 51233 ssh2\n"
            "Failed password for root from 198.51.100.9 port 41022 ssh2\n```\n\n"
            "`sshd_config` (relevant part):\n"
            "```\nPermitRootLogin yes\nPasswordAuthentication yes\n```"
        ),
        "ask": "Diagnose the exposure and propose a fix.",
        "key_points": [
            "PermitRootLogin yes plus PasswordAuthentication yes means the highest-privilege "
            "account is reachable over SSH with only a guessable password, that's what the "
            "brute-force attempts are targeting",
            "the failed attempts alone aren't the vulnerability, the sshd_config allowing "
            "exactly that attack to eventually succeed is",
            "fix: set PermitRootLogin no (or prohibit-password), disable "
            "PasswordAuthentication in favor of key-based auth, and consider fail2ban or "
            "equivalent to rate-limit repeated attempts",
        ],
    },
]


def seed_scenario_catalog(session: Session) -> None:
    if session.exec(select(ScenarioProblem)).first() is not None:
        return  # already seeded, don't touch existing data

    print(f"Seeding scenario catalog ({len(SCENARIO_CATALOG)} scenarios)...")
    for entry in SCENARIO_CATALOG:
        session.add(
            ScenarioProblem(
                title=entry["title"],
                area=entry["area"],
                difficulty=entry["difficulty"],
                situation=entry["situation"],
                ask=entry["ask"],
                key_points=json.dumps(entry["key_points"]),
            )
        )
    session.commit()
