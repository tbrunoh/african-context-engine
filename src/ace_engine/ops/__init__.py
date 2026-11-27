"""Operations for a deployment on Google Cloud: the spend guard and the weekly model check. Nothing here runs on its
own: deploy/gcp/setup.sh deploys each as a Cloud Run service or job, using the ACE image."""
