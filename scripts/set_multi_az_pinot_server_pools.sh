#!/bin/bash

namespace=$1
CONTROLLER=localhost:9000

if [ -z "$namespace" ]; then
namespace="kfuse"
fi

# This script updates the pool config of pinot servers based on the availability zone that is hosting the server.
# It ensures that pods from the same availability zone are configured to have the same pool.
# It also triggers a rebalance of pinot table to set new server instance assignment based on the updated pool
# configuration.

# Get the list of pinot server statefulsets.
pinot_sts=`kubectl get sts -n $namespace -o 'custom-columns=NAME:.metadata.name' | grep pinot | grep server`

for sts in $pinot_sts
do
  echo Updating server instances for $sts
  nodes=`kubectl get pods -n $namespace --no-headers -o 'custom-columns=NODE:.spec.nodeName,CONTROLLER:.metadata.ownerReferences[].name' | grep $sts$ | awk '{print $1}' | sort | uniq`
  zones=`kubectl get nodes $nodes --no-headers -o 'custom-columns=ZONE:.metadata.labels.topology\.kubernetes\.io/zone' | sort | uniq`
  echo $sts is deployed in the following $zones
  for pod in `kubectl get pods -n $namespace --no-headers -o 'custom-columns=NAME:.metadata.name,CONTROLLER:.metadata.ownerReferences[].name' | grep $sts$ | awk '{print $1}'`
  do
    tags=`curl -s -X GET http://$CONTROLLER/instances/Server_$pod.$sts-headless.$namespace.svc.cluster.local_8098 -H 'accept: application/json' --fail | jq -c '.tags[]' -r`
    curr_node=`kubectl get pods $pod -n $namespace --no-headers -o 'custom-columns=NODE:.spec.nodeName'`
    curr_zone=`kubectl get nodes $nodes --no-headers -o 'custom-columns=ZONE:.metadata.labels.topology\.kubernetes\.io/zone'`
    zone_idx=0
    for zone in $zones
    do
      if [[ "$zone" == "$curr_zone" ]]; then
        break
      fi
      zone_idx=$((zone_idx + 1))
    done
    for tag in $tags
    do
      if [[ "$tag" == "kfLogsDimTable_OFFLINE" ]]; then
        continue
      fi
      echo Updating pool for $pod with $tag=$zone_idx
      read -p "Proceed? (y/n)"
      echo    # (optional) move to a new line
      if [[ ! $REPLY =~ ^[Yy]$ ]]
      then
        echo Skipping.
        continue
      fi
      curl -s -X PUT http://$CONTROLLER/instances/Server_$pod.$sts-headless.$namespace.svc.cluster.local_8098/updatePools?pools=$tag=$zone_idx -H 'accept: application/json' --fail
      echo
    done
  done
done

tables=`curl -s -X GET http://$CONTROLLER/tables?type=REALTIME -H 'accept: application/json' --fail | jq -c '.tables[]' -r`
for table in $tables
do
  echo Rebalancing table with updated pool assignment for table $table
  read -p "Proceed? (y/n)"
  echo    # (optional) move to a new line
  if [[ ! $REPLY =~ ^[Yy]$ ]]
  then
    echo Skipping.
    continue
  fi
  curl -X POST 'http://localhost:9000/tables/'$table'/rebalance?type=REALTIME&dryRun=false&reassignInstances=true&includeConsuming=true&minimizeDataMovement=DISABLE&downtime=true&minAvailableReplicas=0'
  echo
done
