# Degraded Kfuse Deployments and Stateful-sets

As a general rule, deployments are are usually setup with at least three replicas.  The reason for this is that with one replica is down, there is at least two others available 
to handle the work. This redundancy allows the system to stay up even with the deployment is degraded.

However, if there are less than 2/3rd of a statefuleset or a deployment available, there is going to be a noticeable impact on performance.  This alert is to give a heads-up that
something is going to have problems.
