# Alert: Pod Failed

## Summary

A Pod Failure is an indication that the application the Pod has failed for one reason or another.  However, the usual reason that a Pod is failing for Kloudfuse is due to *Eviction*.  PODs will not survive scheduling failures, node failures, or other evictions, such as lack of resources, or in the case of node maintenance.

## Common Causes for Eviction

Eviction is a process where a Pod assigned to a Node is asked for termination. One of the most common cases in Kubernetes is Preemption, where in order to schedule a new Pod in a Node with limited resources, another Pod needs to be terminated to leave resources to the first one.

## Resolution

A Pod that has been Evicted, should be deleted.

`k delete po <pod_name>`

After the Pod has been deleted, the StatefulSet, or Deployment will launch a new pod to replace it.
