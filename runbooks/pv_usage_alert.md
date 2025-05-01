# Alert PV Usage exceeded threshold

## Summary

The space allocated to a Persistent Volume Claim(PVC) is nearing a point where it can cause problems to the system.  The address this we will expand the size of the PVC.

## Upgrade PVC allocated space

**Note:** There are vendor specific conditions for related to PVC resizing.  Be aware of those limitions where attempting to resize multiple times.  Refer to the documentation below.

1. Copy the [resize_pvc.sh](https://github.com/kloudfuse/customer/blob/main/scripts/resize_pvc.sh) script to your local environment and make it executable.
2. Verify that the PVC settings that are in the values.YAML

```
  offline:
    persistence:
      size: 16500G
```

3. Get the current size of the PVC from the cluster by running this command

`kubectl get pvc`

![Screenshot 2025-05-01 at 1 04 00 PM](https://github.com/user-attachments/assets/a1d5d525-c00e-4965-b918-8d80528e1598)

The point of this step is to verify if the PVC is different from the default configuration.  You will need to follow internally as to why there was a difference between the 
configured environment and actual implementation.

4.  Run the script to resize the PVC `./resize_pvc.sh ${STATEFUL_SET} ${SIZE} ${KUBE_NAMESPACE}`
NOTE: The default namespace is 'kfuse'

Example: `./resize_pvc.sh pinot-server-offline 281Gi` 

```
+ sts_name=pinot-server-offline
+ size=281Gi
+ namespace=kfuse
+ '[' -z pinot-server-offline ']'
+ '[' -z 281Gi ']'
+ '[' -z kfuse ']'
++ kubectl get pods -n kfuse -o 'custom-columns=NAME:.metadata.name,CONTROLLER:.metadata.ownerReferences[].name'
++ grep 'pinot-server-offline$'
++ awk '{print $1}'
+ for pod in '`kubectl get pods -n $namespace -o '\''custom-columns=NAME:.metadata.name,CONTROLLER:.metadata.ownerReferences[].name'\'' | grep $sts_name$ | awk '\''{print $1}'\''`'
++ kubectl get pods -n kfuse pinot-server-offline-0 -o 'custom-columns=PVC:.spec.volumes[].persistentVolumeClaim.claimName'
++ grep -v PVC
+ for pvc in '`kubectl get pods -n $namespace $pod -o '\''custom-columns=PVC:.spec.volumes[].persistentVolumeClaim.claimName'\'' | grep -v PVC`'
+ echo Patching data-pinot-server-offline-0
Patching data-pinot-server-offline-0
+ echo 'kubectl patch pvc data-pinot-server-offline-0 -n kfuse --patch '\''{"spec": {"resources": {"requests": {"storage": "'\''281Gi'\''" }}}}'\'''
kubectl patch pvc data-pinot-server-offline-0 -n kfuse --patch '{"spec": {"resources": {"requests": {"storage": "'281Gi'" }}}}'
+ kubectl patch pvc data-pinot-server-offline-0 -n kfuse --patch '{"spec": {"resources": {"requests": {"storage": "281Gi" }}}}'
persistentvolumeclaim/data-pinot-server-offline-0 patched
+ '[' 0 -ne 0 ']'
+ echo 'saving old sts pinot-server-offline yaml'
saving old sts pinot-server-offline yaml
+ kubectl -n kfuse get sts pinot-server-offline -o yaml
+ echo 'creating updated sts pinot-server-offline yaml'
creating updated sts pinot-server-offline yaml
+ sed 's/storage:.*/storage: 281Gi/g' old_pinot-server-offline.yaml
+ echo 'kubectl delete sts pinot-server-offline --cascade=orphan -n kfuse'
kubectl delete sts pinot-server-offline --cascade=orphan -n kfuse
+ kubectl delete sts pinot-server-offline --cascade=orphan -n kfuse
statefulset.apps "pinot-server-offline" deleted
+ echo 'applying updated pinot-server-offline yaml'
applying updated pinot-server-offline yaml
+ kubectl apply -f updated_pinot-server-offline.yaml
statefulset.apps/pinot-server-offline created
+ echo Make sure that the helm values.yaml reflects the updated disk size.
Make sure that the helm values.yaml reflects the updated disk size.
```

5. Rerun `kubectl get pvc` and verify that the changes have taken effect. It make take up to a minute for all the changes to completed.

6. Update your values.yaml with the update size for the PVC.  If you do not it will give you error an error when you attempt to run helm upgrade

```
The PersistentVolumeClaim "data-pinot-server-offline-0" is invalid: spec.resources.requests.storage: Forbidden: field can not be less than previous value
+ '[' 1 -ne 0 ']'
```

## Vendor Notes

### AWS 

#### Elastic Volumes

[Request Amazon EBS volume modifications - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/requesting-ebs-volume-modifications.html)  

Keep the following in mind when modifying volumes:

> * After modifying a volume, **you must wait at least six hours and ensure that the volume is in the in-use or available state before you can modify the same volume.**
> * **Modifying an EBS volume can take from a few minutes to a few hours**, depending on the configuration changes being applied. An EBS volume that is 1 TiB in size can typically take up to six hours to be modified. However, the same volume could take 24 hours or longer in other situations. The time it takes for volumes to be modified doesn't always scale linearly. Therefore, a larger volume might take less time, and a smaller volume might take more time.
> * **You can't cancel a volume modification request after it has been submitted.**
> * **You can only increase volume size. You can't decrease volume size.**
> * **You can increase or decrease volume performance.**
> * If you are not changing the volume type, then volume size and performance modifications must be within the limits of the current volume type. If you are changing the volume type, then volume size and performance modifications must be within the limits of the target volume type
> * If you change the volume type from gp2 to gp3, and you do not specify IOPS or throughput performance, Amazon EBS automatically provisions either equivalent performance to that of the source gp2 volume, or the baseline gp3 performance, whichever is higher.

### GCP

#### Extreme Persistent Disks

[Extreme persistent disks  |  Compute Engine Documentation  |  Google Cloud](https://cloud.google.com/compute/docs/disks/extreme-persistent-disk)

Extreme persistent disks feature higher maximum IOPS and throughput, and allow you to provision IOPS and capacity separately. Extreme persistent disks are available in all zones.

[Increase the size of a persistent disk  |  Compute Engine Documentation  |  Google Cloud ](https://cloud.google.com/compute/docs/disks/resize-persistent-disk)

**Note:** You can resize an Extreme Persistent Disk only once in a 6 hour period.

#### Resizing Persistent Volume Claim

[Using volume expansion  |  Google Kubernetes Engine (GKE)  |  Google Cloud ](https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/volume-expansion#using_volume_expansion)

**Note:** You will need to add allowVolumeExpansion: true to your StorageClass, if your StorageClass doesn't already have the field.

### Azure

#### Changing Performance Tier

[Change the performance of Azure managed disks - Azure Virtual Machines](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-performance-tiers?utm_source=chatgpt.com&tabs=azure-cli)

Changing the performance tier is currently only supported for Premium SSD managed disks.
Performance tiers of shared disks can't be changed while attached to running VMs.
To change the performance tier of a shared disk, stop all the VMs the disk is attached to.
Only disks larger than 4,096 GiB can use the P60, P70, and P80 performance tiers.
A disk's performance tier can be downgraded only once every 12 hours.
The system doesn't return Performance Tier for disks created before June 2020. You can take advantage of Performance Tier for an older disk by updating it with the baseline Tier.
You can't set a disk's performance tier to a tier below its baseline tier.

#### Resizing Persistent Volume Claim

[Resize persistent volume claim (PVC) for Azure Arc-enabled data services volume - Azure Arc](https://learn.microsoft.com/en-us/azure/azure-arc/data/resize-persistent-volume-claim) 

Resizing PVCs using this method only works your StorageClass supports AllowVolumeExpansion=True


