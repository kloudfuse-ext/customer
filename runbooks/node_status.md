# Kubernetes Node Status

## Summary

A node, when healthy, is in a *Ready* condition and can accept Pods.  If a node is under stress it can be unable to
run new nodes, and will no longer in be a "Ready* condition.

A node may also be unschedulable.  Meaning Kubernetes cannot schedule any new pods to run on that node.

## Node Conditions

You can refer to the [official documentation](https://kubernetes.io/docs/reference/node/node-status/#condition)  Listed below are 
the default conditions, though more many supported by the cluster vendor.

| Condition | Description |
--- | --- 
| Ready	              | <ul><li>**True** if the node is healthy and ready to accept pods</li><li>**False** if the node is not healthy and is not accepting pods</li><li>**Unknown** if the node controller has not heard from the node in the last node-monitor-grace-period (default is 50 seconds)</li></ul> |
| DiskPressure	      | **True** if pressure exists on the disk size—that is, if the disk capacity is low; otherwise **False** |
| MemoryPressure	    | **True** if pressure exists on the node memory—that is, if the node memory is low; otherwise **False** |
| PIDPressure	        | **True** if pressure exists on the processes—that is, if there are too many processes on the node; otherwise **False** |
| NetworkUnavailable	| **True** if the network for the node is not correctly configured, otherwise **False** |

If  a pod is not in a Ready state, it will not be able to run an new pods.  The verify this you can describe the node and check the Conditions section

```
kubernetes describe node <NODE_NAME>

[…]
Conditions:
  Type                                              Status  LastHeartbeatTime                                                               ------  -----------------
  DeprecatedUsingV1Alpha2Cri                        False   Wed, 14 May 2025 16:13:31 -0700...
  DeprecatedAuthsFieldInContainerdConfiguration     False   Wed, 14 May 2025 16:13:31 -0700...
  FrequentKubeletRestart                            False   Wed, 14 May 2025 16:13:31 -0700...
  Ready                                             True    Wed, 14 May 2025 16:15:49 -0700...
```

### DiskPressure

[This article](https://www.groundcover.com/blog/kubernetes-disk-pressure) goes over the "DiskPresure" condition and how to fix them.

## Unschedulable Nodes

If a node that has cordoned, Kubernetes will mark it unschedulable. A cordoned node can continue to host the pods it is already running, 
but cannot accept new pods. To verify this you can describe the node and check the Unschedulable field,

```
kubectl describe node <NODE_NAME>

[…]
Unschedulable:      true
```

If a node has been cordoned, you should verify the reason it is such a state.  Usually it is put into cordon state for maintenance reasons.

It can be uncordoned by running,

```
kubectl uncordon <NODE_NAME>
```




You can refer to more details about [Unschedulable Nodes here](https://www.datadoghq.com/blog/debug-kubernetes-pending-pods/#unschedulable-nodes)

