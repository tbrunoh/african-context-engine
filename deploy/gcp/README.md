# ACE on Google Cloud

These files stand up the stack that runs [ace.korext.com](https://ace.korext.com) in any Google Cloud project, from a checkout of a release, with no fork.

| Piece | What it is |
| --- | --- |
| `ace-web` | Cloud Run service: the site, the /try phone and the API (gunicorn, one warm instance, at most ten) |
| `ace-mcp` | Cloud Run service: MCP over Streamable HTTP at /mcp, stateless (scales to zero, at most five) |
| `ace-refresh` | Cloud Run job: refreshes snapshots into a copy of the set in use, checks them, and publishes the set only if every check passes |
| Load balancer | Global Application Load Balancer with a Google-managed certificate, TLS 1.2 or later, an HTTP to HTTPS redirect (the HTTP listener marks the request and `ace-web` redirects it to `ACE_HTTPS_HOST`, because Google's own redirect adds :443 to the address), HSTS, and Cloud Armor limits per address; /mcp goes to `ace-mcp`, everything else to `ace-web`. Both services take traffic only from it |
| Firestore | Web sessions (24 hour expiry) and escalation counts with no text, in the same region |
| Cloud Storage | Snapshot sets, mounted read only into both services; sets older than seven days are deleted, never the one in use |
| Cloud Scheduler | Warnings every hour, weather twice a day, market prices every Monday, the model check every Tuesday, the spend meter every ten minutes |
| `ace-guard` | Cloud Run service that holds the project under its monthly cap: it meters spending every ten minutes and, as the cap nears, turns the language model off, pauses the site and MCP, closes the edge in Cloud Armor, and as a last step removes the forwarding rules |
| `ace-modelcheck` | Cloud Run job: runs ACE's grounding checks on the newest Gemini Flash model and pins the last good one if it fails |

## Stand it up

```
git clone https://github.com/tbrunoh/african-context-engine && cd african-context-engine
git checkout v2.4.2
PROJECT=your-project DOMAIN=ace.example.org bash deploy/gcp/setup.sh
```

The budget goes on the billing account linked to the project; set `BILLING_ACCOUNT` to use another.

The script prints the load balancer's address at the end. Add an A record for your domain pointing to it; the certificate becomes active within about an hour of the record resolving. Then:

```
python3 deploy/gcp/smoke.py https://ace.example.org
```

Both services answer only through the load balancer, where Cloud Armor, HSTS and the TLS policy apply. To test before the domain resolves, run the script with `INGRESS=all`, then run it again without.

In an organisation that enforces domain restricted sharing, the script makes both services public by turning off Cloud Run's invoker IAM check, which Google recommends for this case, rather than by granting `allUsers`. The budget cannot publish its alerts to Pub/Sub there either, so it sends email alerts only; the spend cap does not depend on it (see below). A daily Gemini request quota adds a second ceiling on the one charge that grows with use, as ace.korext.com has:

```
gcloud beta quotas preferences create --service=generativelanguage.googleapis.com \
  --quota-id=GenerateRequestsPerDayPerProjectPerModel --preferred-value=1000 --preference-id=ace-gemini-daily \
  --project=PROJECT --billing-project=PROJECT --allow-quota-decrease-below-usage --allow-high-percentage-quota-decrease
```

To use Gemini, store an API key first as the secret `ace-gemini-key` (Secret Manager, in your region). Without it, ACE answers by extraction only, which is complete and cited; the model only rephrases.

## Release

```
gcloud builds submit --region africa-south1 --config deploy/gcp/cloudbuild.yaml \
  --service-account projects/PROJECT/serviceAccounts/ace-build@PROJECT.iam.gserviceaccount.com \
  --substitutions _IMAGE=africa-south1-docker.pkg.dev/PROJECT/ace/ace:TAG,_COMMIT=$(git rev-parse HEAD),_DOMAIN=ace.example.org .
```

Cloud Build runs Ruff, the tests and the quick benchmark, builds one image, gives the new `ace-web` and `ace-mcp` revisions the `candidate` tag with no traffic, runs the smoke suite against both through the load balancer with the secret `x-ace-candidate` header, checks that both run the commit just built, and only then moves traffic. The refresh job, the guard and the model check follow. To roll back, move traffic to the previous revision in the Cloud Run console or with `gcloud run services update-traffic ace-web --to-revisions REVISION=100`.

## What it costs, and the cap

At demonstration traffic about $45 a month, most of it fixed: the load balancer's forwarding rules (about $18), the warm `ace-web` instance (about $13) and Cloud Armor (about $8). Firestore, Cloud Storage, logging, Artifact Registry and Secret Manager stay under $3.

A Google Cloud budget only sends alerts, so the project caps itself. Every ten minutes Cloud Scheduler calls `ace-guard` at /meter. It reads month to date usage from Cloud Monitoring (Cloud Run time and requests, load balancer requests and bytes, Gemini calls, Firestore and Cloud Storage operations), prices it at list prices with no free tier counted, adds the fixed charges for every hour so far, and asks whether the month could still end above the cap (`BUDGET_USD`, $60 by default) if traffic stopped now. Each step below is taken only when it is needed to keep that answer no:

| Level | What the guard does | What still costs money |
| --- | --- | --- |
| 1 | Turns the language model off; ACE answers by extraction | Everything else |
| 2 | Pauses the site and MCP; no warm instance | Forwarding rules, Cloud Armor, requests that arrive |
| 3 | Cloud Armor turns every request away at the edge | Forwarding rules, Cloud Armor per request |
| 4 | Removes the two forwarding rules | The reserved address, the Armor policy, storage |

Gemini is priced from the tokens `ace-web` counts for each call, at or above the highest Flash list price; a call it did not count (the weekly model check) is priced at the most one call can cost, 3,000 tokens in and 1,024 out. The month's highest level is kept in Firestore, so the level only rises within a month, and a failed read changes nothing until the next run; on the 1st the guard restores everything, forwarding rules included. Each run logs its estimate line by line under the message spend guard. To see it without changing anything, run `python -m ace_engine.ops.meter` with `ACE_GUARD_PROJECT` set, or set `ACE_GUARD_ENFORCE=0` on `ace-guard`. One limit stays: the meter acts every ten minutes, so a flood of requests far beyond anything ACE serves could add a few dollars in the minutes before Cloud Armor closes; the margin each level keeps (from $6 down to $0.75) is there for that.

## Privacy

No phone number is stored. Web sessions carry a random key; profiles hold only what improves the next answer and expire after 24 hours; escalations are counted with no text; application logs record no message text. Logs go to a bucket in the deployment's region with 30 day retention.
