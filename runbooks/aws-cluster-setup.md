# AWS EKS Cluster Setup for Kloudfuse (kfuse)

> **Verified for EKS version 1.31**

This guide provides step-by-step instructions to set up an Amazon EKS cluster with recommended IAM roles, node groups, and add-ons, and to prepare the environment for Kloudfuse (kfuse) installation.

## Prerequisites
- AWS CLI and `eksctl` installed and configured (for later steps)
- kubectl installed
- Sufficient AWS permissions to create EKS clusters, IAM roles, and policies

---

## 1. Create an EKS Cluster (AWS Console)

1. **Create the EKS cluster from the AWS Console:**
   - Go to the EKS section in the AWS Console.
   - Click "Create cluster".
   - Use the standard Amazon EKS optimized AMI (the default image in the dropdown).
   - For the cluster service role, click "Create new role" and let AWS create the recommended role for you.
   - Complete the rest of the cluster creation steps as per your requirements.

---

## 2. Install EKS Add-ons

Install the following add-ons:
- kube-proxy
- core-dns
- ebs-csi (EBS plugin)
- vpc-cni (CNI plugin)

### a. Associate OIDC Provider

```sh
eksctl utils associate-iam-oidc-provider \
  --cluster <cluster-name> \
  --approve
```

### b. Create IAM Service Accounts for Add-ons (using IRSA)

#### CNI Plugin (aws-node)
```sh
eksctl create iamserviceaccount \
  --name aws-node \
  --namespace kube-system \
  --cluster <cluster-name> \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy \
  --approve \
  --override-existing-serviceaccounts
```

#### EBS CSI Plugin
```sh
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster <cluster-name> \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonEBSCSIDriverPolicy \
  --approve \
  --override-existing-serviceaccounts
```

#### Install Add-ons
- Add the following add-ons from the AWS Console under your EKS cluster's "Add-ons" tab:
  - kube-proxy
  - core-dns
  - ebs-csi (EBS plugin)
  - vpc-cni (CNI plugin)
- For ebs-csi and vpc-cni, select the respective IAM roles (IRSA) you created in the previous step when prompted for service account roles.

---

## 3. Create a Node Group (AWS Console)

1. **Create a node group from the AWS Console:**
   - In your EKS cluster, go to the "Compute" tab and click "Add node group".
   - Use the default settings for AMI and instance type as per your needs.
   - When prompted for the node IAM role, click "Create new role" and let AWS create the recommended role.
   - After creation, ensure the node group IAM role has the following AWS managed policies attached:
     - `AmazonS3FullAccess`
     - `AmazonEKSWorkerNodePolicy`
     - `AmazonEKS_CNI_Policy`
     - `AmazonEC2ContainerRegistryReadOnly`
   - If any policy is missing, attach it via the AWS Console or CLI:
     ```sh
     aws iam attach-role-policy \
       --role-name <node-role-name> \
       --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
     ```

---

## 4. Verify Add-ons

Check that all pods in the `kube-system` namespace are running:
```sh
kubectl get pods -n kube-system
```

---

## 5. Install Kloudfuse (kfuse)

Follow the official installation instructions: [Kloudfuse Install Guide](https://docs.kloudfuse.com/platform/latest/install/)

---

## 6. Configure kfuse Namespace Service Account to Use Node Role

1. **Update Node Role Trust Policy**
   - Edit the node role's trust policy to allow the `kfuse:default` service account to assume the role via OIDC:
   - **To get your OIDC URL, run:**
     ```sh
     aws eks describe-cluster \
       --name <your-cluster-name> \
       --query "cluster.identity.oidc.issuer" \
       --output text
     ```
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Service": "ec2.amazonaws.com"
         },
         "Action": "sts:AssumeRole"
       },
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::<aws-account-id>:oidc-provider/<oidc-provider-url>"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "<oidc-provider-url>:sub": "system:serviceaccount:kfuse:default"
           }
         }
       }
     ]
   }
   ```

   **Example:**
   ```json
   {
     "Effect": "Allow",
     "Principal": {
       "Federated": "arn:aws:iam::119999443945:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/4A021F22222F9D6065B62CD6666B09A9"
     },
     "Action": "sts:AssumeRoleWithWebIdentity",
     "Condition": {
       "StringEquals": {
         "oidc.eks.us-west-2.amazonaws.com/id/4A021F22222F9D6065B62CD6666B09A9:sub": "system:serviceaccount:kfuse:default"
       }
     }
   }
   ```

2. **Patch the Service Account in kfuse Namespace:**
   ```sh
   kubectl patch serviceaccount default \
     -n kfuse \
     -p '{"metadata": {"annotations": {"eks.amazonaws.com/role-arn": "<arn of node role>"}}}'
   ```

3. **Restart Pinot StatefulSets to pick up the new role:**
   ```sh
   kubectl rollout restart sts -n kfuse pinot-server-realtime pinot-server-offline pinot-controller
   ```

---

## 7. Verify Setup

- Ensure all pods in the `kfuse` namespace are running:
  ```sh
  kubectl get pods -n kfuse
  ```
- Pinot services should now be able to use the node role and access the S3 bucket.
- Log in to the kfuse UI to continue setup.

---

## References
- [EKS IAM Roles for Service Accounts (IRSA)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Kloudfuse Documentation](https://docs.kloudfuse.com/platform/latest/install/)
