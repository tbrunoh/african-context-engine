# ACE on Google Cloud

These files stand up the stack that runs [ace.korext.com](https://ace.korext.com) in any Google Cloud project, from a checkout of a release, with no fork.

| Piece | What it is |
| --- | --- |
| `ace-web` | Cloud Run service: the site, the /try phone and the API (gunicorn, one warm instance, at most ten) |
| `ace-mcp` | Cloud Run service: MCP over Streamable HTTP at /mcp, stateless (scales to zero, at most five) |
| `ace-refresh` | Cloud Run job: refreshes snapshots into a copy of the set in use, checks them, and publishes the set only if every check passes |
| Load balancer | Global Application Load Balancer with a Google-managed certificate, TLS 1.2 or later, an HTTP to HTTPS redirect, HSTS, and Cloud Armor limits per address; /mcp goes to `ace-mcp`, everything else to `ace-web`. Both services take traffic only from it |
| Firestore | Web sessions (24 hour expiry) and escalation counts with no text, in the same region |
| Cloud Storage | Snapshot sets, mounted read only into both services; sets older than seven days are deleted, never the one in use |
| Cloud Scheduler | Warnings every hour, weather twice a day, market prices every Monday, the model check every Tuesday |
| `ace-guard` | Cloud Run service on a Pub/Sub push: at 90% of the monthly budget it turns the language model off; at 100% it pauses the site and MCP and lets both scale to zero |
| `ace-modelcheck` | Cloud Run job: runs ACE's grounding checks on the newest Gemini Flash model and pins the last good one if it fails |

## Stand it up

```
git clone https://github.com/tbrunoh/african-context-engine && cd african-context-engine
git checkout v2.4.0b1
PROJECT=your-project DOMAIN=ace.example.org bash deploy/gcp/setup.sh
```

The budget goes on the billing account linked to the project; set `BILLING_ACCOUNT` to use another.

The script prints the load balancer's address at the end. Add an A record for your domain pointing to it; the certificate becomes active within about an hour of the record resolving. Then:

```
python3 deploy/gcp/smoke.py https://ace.example.org
```

Both services answer only through the load balancer, where Cloud Armor, HSTS and the TLS policy apply. To test before the domain resolves, run the script with `INGRESS=all`, then run it again without.

To use Gemini, store an API key first as the secret `ace-gemini-key` (Secret Manager, in your region). Without it, ACE answers by extraction only, which is complete and cited; the model only rephrases.

## Release

```
gcloud builds submit --region africa-south1 --config deploy/gcp/cloudbuild.yaml \
  --service-account projects/PROJECT/serviceAccounts/ace-build@PROJECT.iam.gserviceaccount.com \
  --substitutions _IMAGE=africa-south1-docker.pkg.dev/PROJECT/ace/ace:TAG,_COMMIT=$(git rev-parse HEAD),_DOMAIN=ace.example.org .
```

Cloud Build runs Ruff, the tests and the quick benchmark, builds one image, gives the new `ace-web` revision the `candidate` tag with no traffic, runs the smoke suite against it through the load balancer with the secret `x-ace-candidate` header, and only then moves traffic. `ace-mcp`, the refresh job, the guard and the model check follow. To roll back, move traffic to the previous revision in the Cloud Run console or with `gcloud run services update-traffic ace-web --to-revisions REVISION=100`.

## What it costs

At demonstration traffic about $45 a month, most of it fixed: the load balancer's forwarding rules (about $18), the warm `ace-web` instance (about $13) and Cloud Armor (about $9 to $10). Firestore, Cloud Storage, logging, Artifact Registry and Secret Manager stay under $2. Gemini is capped separately. The budget only alerts; `ace-guard` is what acts on it.

## Privacy

No phone number is stored. Web sessions carry a random key; profiles hold only what improves the next answer and expire after 24 hours; escalations are counted with no text; application logs record no message text. Logs go to a bucket in the deployment's region with 30 day retention.
