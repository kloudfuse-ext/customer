# Alert Pod experiencing magePullBackOff Error

## Summary

When a Pod is created, Kubernetes pulls the container image from a registry (like Docker Hub, Amazon ECR, etc.). If it can't do this, it enters the ImagePullBackOff state. This state comes after a failed pull attempt (typically ErrImagePull), and Kubernetes starts retrying with exponential backoff.

## Common Causes

### Incorrect image name or tag
Example: Typo in image like ngnix:latest instead of nginx:latest.

### Image doesn’t exist
Trying to pull an image that hasn't been pushed to the registry.

### Private registry and missing credentials
Pod can't access a private image because of missing imagePullSecrets.

### Authentication issues
Wrong credentials or expired access tokens.

### Network issues
Cluster can't reach the image registry due to firewall, DNS issues, or lack of internet.

## How to Troubleshoot

### Check Pod status and events 

Run `kubectl describe pod <pod-name>`  Look for messages under Events:

like:

`Failed to pull image "myapp:v1": rpc error: code = Unknown desc = Error response from daemon: pull access denied`

### Check image name and tag

Make sure the image exists and is spelled correctly.

### Verify imagePullSecrets (for private registries)

Run `kubectl describe pod <pod-name>`  Look for imagePullsecrets

```
imagePullSecrets:
- name: my-registry-secret
```

The `name` refers to secret that has the image credentials.  Verify that the secret exists by running

`kubectl get secret <secret-name>`

#### Ensure nodes have internet access

Verify internet access from the cluster by doing to do a curl to the repo

`curl https://us.gcr.io/mvp-demo-301906`





