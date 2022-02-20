import time
import kopf
import kubernetes
import yaml
import os
from environs import Env
from kubernetes.client.rest import ApiException
from pprint import pprint
import datetime
import random
import json
import asyncio
# for operator version
from __version__ import __version__

       
REPLICAS_ANNOTATON="shutdown.djkormo.github/replicas"       
TIMESTAMP_ANNOTATION="shutdown.djkormo.github/changedAt"

# use env variable to control loop interval in seconds
try:
  LOOP_INTERVAL = int(os.environ['LOOP_INTERVAL'])
except:
  LOOP_INTERVAL=30
  print(f"Variable LOOP_INTERVAL is not set, using {LOOP_INTERVAL}s as default")       

try:
  EXCLUDED_NAMESPACES = os.environ['EXCLUDED_NAMESPACES']
except:
  EXCLUDED_NAMESPACES="kube-system,kube-public,kube-node-lease"
  print(f"Variable EXCLUDED_NAMESPACES is not set, using {EXCLUDED_NAMESPACES} as default")    


try:
  NAMESPACE = os.environ['NAMESPACE']
except:
  NAMESPACE="default"
  print(f"Variable NAMESPACE is not set, using {NAMESPACE} as default")    


# check if namespace should be under operator control

def check_namespace(name,excluded_namespaces):
  env = Env()
  env.read_env()  # read .env file, if it exists
  namespace_list = env.list(excluded_namespaces)
  if name in namespace_list:
    print(f"Excluded namespace list: {namespace_list} ")    
    print(f"Excluded namespace found: {name}")
    return True
  else:
     return False  

# Deployment start     

# Turning off deployment

def turn_off_deployment(name,namespace,logger,kopf,metadata,spec,api,dry_run):
  logger.info("Turning off Deployment %s in namespace %s", name,namespace)
  
  # how many replicas we have
  replicas = spec.replicas
  replicas = str(replicas)

  logger.info("Deployment %s in %s namespace has %s replicas", name,namespace,replicas)
  
  # save replicas and timestamp to proper annotations
  
  now = datetime.datetime.utcnow()
  now = str(now.isoformat("T") + "Z")

  body = {
                "metadata": {
                    "annotations": {
                        REPLICAS_ANNOTATON: replicas,
                        TIMESTAMP_ANNOTATION: now
                    }
                }
    }

  if (not dry_run):
    try:
      api_response =api.patch_namespaced_deployment(name, namespace, body=body)
    except ApiException as e:
      if e.status == 404:
        logger.error("No deployment found")
      else:
        logger.error("Exception when calling AppsV1Api->patch_namespaced_deployment: %s\n" % e)


  if (not dry_run):
    # set replicas to zero
    logger.info("Setting Deployment %s in %s namespace to zero replicas",name,namespace)

    body = {"spec": {"replicas": 0}}

    try:
      api_response =api.patch_namespaced_deployment_scale(name, namespace, body=body)
    except ApiException as e:
      if e.status == 404:
         logger.error("No deployment found")
      else:
        logger.error("Exception when calling AppsV1Api->patch_namespaced_deployment_scale in turn_off_deployment : %s\n" % e)
  

# Turning on deployment     
def turn_on_deployment(name,namespace,logger,kopf,metadata,spec,api,dry_run):
    logger.info("Turning on Deployment %s in namespace %s", name,namespace)
  
    replicas=metadata.annotations[REPLICAS_ANNOTATON]
    replicas=int(replicas)
    if (not dry_run):
      logger.info("Setting Deployment %s in %s namespace to %s replicas",name,namespace,replicas)

      body = {"spec": {"replicas": replicas}}

      try:
        api_response =api.patch_namespaced_deployment_scale(name, namespace, body=body)
      except ApiException as e:
        if e.status == 404:
          logger.error("No deployment found")
        else:
          logger.error("Exception when calling AppsV1Api->patch_namespaced_deployment_scale in turn_on_deployment: %s\n" % e)

# Deployment end


# Daemonset start   

# Turning off daemonset

def turn_off_daemonset(name,namespace,logger,kopf,metadata,spec,status,api,dry_run,node_selector):
  logger.info("Turning off Daemonset %s in namespace %s", name,namespace)  
  now = datetime.datetime.utcnow()
  now = str(now.isoformat("T") + "Z")
  replicas=status.desired_number_scheduled
  replicas=str(replicas)
  body = {
            'metadata': {
              'annotations': {
                  REPLICAS_ANNOTATON: replicas,
                  TIMESTAMP_ANNOTATION: now
                  }
                }
    }

    
  if (not dry_run):
    try:
      api_response =api.patch_namespaced_daemon_set(name, namespace, body=body)
    except ApiException as e:
      if e.status == 404:
        logger.error("No daemonset found")
      else:
        logger.error("Exception when calling AppsV1Api->patch_namespaced_daemonset_set in turn_off_daemonset : %s\n" % e)
  
  node_selector=str(node_selector)
  body={"spec": {"template": {"spec": {"nodeSelector": {node_selector: "true"}}}}}

  if (not dry_run):
    try:
      api_response =api.patch_namespaced_daemon_set(name, namespace, body=body)
    except ApiException as e:
      if e.status == 404:
        logger.error("No daemonset found")
      else:
        logger.error("Exception when calling AppsV1Api->patch_namespaced_daemonset_set: %s\n" % e)

 

# Turning on daemonset  

def turn_on_daemonset(name,namespace,logger,kopf,metadata,spec,status,api,dry_run,node_selector):
    logger.info("Turning on Daemonset %s in namespace %s", name,namespace)
    node_selector=str(node_selector)
    path_selector=str('/spec/template/spec/nodeSelector/')+str(node_selector)
    body=[{'op': 'remove', 'path': path_selector }]
    logger.info("Turning on Daemonset %s patch %s",name, body)
   
    if (not dry_run):
      try:

        api_response =api.patch_namespaced_daemon_set(name, namespace, body=body)
      except ApiException as e:
        if e.status == 404:
          logger.error("No daemonset found")
        else:
          logger.error("Exception when calling AppsV1Api->patch_namespaced_daemonset_set in turn_on_daemonset: %s\n" % e)


# Daemonset end  

# Statefulset start  

# Turning off statefulset

def turn_off_statefulset(name,namespace,logger,kopf,metadata,spec,api,dry_run):
  logger.info("Turning off Statefulset %s in namespace %s", name,namespace) 
  # how many replicas we have
  replicas = spec.replicas
  replicas = str(replicas)
  logger.info("Statefulset %s in %s namespace has %s replicas", name,namespace,replicas)

  # save replicas to proper annotation 
  now = datetime.datetime.utcnow()
  now = str(now.isoformat("T") + "Z")

  body = {
                'metadata': {
                    'annotations': {
                        REPLICAS_ANNOTATON: replicas,
                        TIMESTAMP_ANNOTATION: now
                    }
                }
    }
  
  if (not dry_run):
    try:
      api_response =api.patch_namespaced_stateful_set(name, namespace, body=body)

    except ApiException as e:
      if e.status == 404:
        logger.error("No statefulset found")
      else:
        logger.error("Exception when calling AppsV1Api->patch_namespaced_statefulset_scale in turn_off_statefulset: %s\n" % e)


  if (not dry_run):
    # set replicas to zero
    logger.info("Setting Statefulset %s in %s namespace to zero replicas",name,namespace)
    body = {"spec": {"replicas": 0}}
    try:
      api_response =api.patch_namespaced_stateful_set_scale(name, namespace, body=body)

    except ApiException as e:
      if e.status == 404:
        logger.error("No statefulset found")
      else:
        logger.error("Exception when calling AppsV1Api->patch_namespaced_stateful_set_scale in turn_off_statefulset : %s\n" % e)
     

# Turning on statefulset

def turn_on_statefulset(name,namespace,logger,kopf,metadata,spec,api,dry_run):
    logger.info("Turning on Statefulset %s in namespace %s", name,namespace)   
    if (not dry_run):
      # set replicas to previous number 
      replicas=metadata.annotations[REPLICAS_ANNOTATON]
      replicas=int(replicas)
      logger.info("Setting Statefulset %s in %s namespace to %s replicas",name,namespace,replicas)
      body = {"spec": {"replicas": replicas}} 
      try:
        api_response=api.patch_namespaced_stateful_set_scale(name, namespace, body=body)

      except ApiException as e:
        if e.status == 404:
          logger.error("No statefulset found")
        else:
          logger.error("Exception when calling AppsV1Api->patch_namespaced_stateful_set_scale in turn_on_statefulset: %s\n" % e)

# Statefulset end
 
 

# Operator configuration start   


@kopf.on.startup()
async def startup_fn_simple(logger:kopf.Logger, settings: kopf.OperatorSettings, memo: kopf.Memo, **kwargs):
    settings.persistence.finalizer = 'shutdown-operator/kopf-finalizer'
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(prefix='shutdown-operator')
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage(
        prefix='shutdown-operator',
        key='last-handled-configuration',
    )

    logger.info('Environment variables:')
    for k, v in os.environ.items():
      logger.info(f'{k}={v}')
    logger.info('Starting in 5s...')
    await asyncio.sleep(5)
    
# for Kubernetes probes

@kopf.on.probe(id='now')
def get_current_timestamp(**kwargs):
    return datetime.datetime.utcnow().isoformat()

@kopf.on.probe(id='random')
def get_random_value(**kwargs):
    return random.randint(0, 1_000_000)
# return version of operator  
@kopf.on.probe(id="version")
def version_probe(**kwargs):
    return __version__
    


# Operator configuration end   


# Operator logic start   



# When creating or resuming object
# Trigerring by the loop every LOOP_INTERVAL seconds 
@kopf.on.resume('djkormo.github', 'v1alpha1', 'shutdown')
@kopf.on.create('djkormo.github', 'v1alpha1', 'shutdown')
@kopf.on.update('djkormo.github', 'v1alpha1', 'shutdown')
@kopf.on.timer('djkormo.github', 'v1alpha1', 'shutdown',interval=LOOP_INTERVAL,sharp=True)
def check_shutdown_on_time_operator(spec, name, namespace, logger, **kwargs):
  logger.info(f"Timer: for {name} with {spec} is invoked")
        
  object_namespace = spec.get('namespace')   
  dry_run = spec.get('dry-run',False)
  deployments_enabled = spec.get('deployments',False)
  daemonsets_enabled = spec.get('daemonsets',False)
  statefulsets_enabled = spec.get('statefulsets',False)
  state = spec.get('state',True)
  node_selector = spec.get('node-selector','shutdown-non-existing')
  label_selector=spec.get('label-selector','')
  
  logger.info("Label selector : %s",label_selector)
  
  # check for excluded namespace
  if check_namespace(name=name,excluded_namespaces='EXCLUDED_NAMESPACES'):
    return {'shutdown-operator-name': namespace}   
     
  # check if deployment is turned on

  api = kubernetes.client.AppsV1Api()

  # Turning off state and deployments are under control
  if deployments_enabled and state:
    try:
      if label_selector=='':
        api_response = api.list_namespaced_deployment(namespace=object_namespace)
      else:
        api_response = api.list_namespaced_deployment(namespace=object_namespace,label_selector=label_selector)
      logger.info ("Found %d deploy to turn off",len(api_response.items))      
      for d in api_response.items:
        logger.info("Deployment %s has %s available replicas of %s desired replicas", d.metadata.name,d.status.available_replicas,d.spec.replicas)
        if d.spec.replicas>0 :
          turn_off_deployment(name=d.metadata.name,namespace=d.metadata.namespace,logger=logger,kopf=kopf,metadata=d.metadata,spec=d.spec,api=api,dry_run=dry_run)
    except ApiException as e:
      logger.error("Exception when calling AppsV1Api->list_namespaced_deployment: %s\n" % e)

  # Turning on state and deployments are under control
  if deployments_enabled and not state:
    try:
      if label_selector=='':
        api_response = api.list_namespaced_deployment(namespace=object_namespace)
      else: 
        api_response = api.list_namespaced_deployment(namespace=object_namespace,label_selector=label_selector)
      logger.info ("Found %d deploy to turn on",len(api_response.items))  
      for d in api_response.items:
        logger.debug("Deployment %s has %s available replicas of %s desired replicas", d.metadata.name,d.status.available_replicas,d.spec.replicas)
        if d.spec.replicas==0 :
          turn_on_deployment(name=d.metadata.name,namespace=d.metadata.namespace,logger=logger,kopf=kopf,metadata=d.metadata,spec=d.spec,api=api,dry_run=dry_run)
    except ApiException as e:
      logger.error("Exception when calling AppsV1Api->list_namespaced_deployment: %s\n" % e)


  # Turning off state and deamonsets are under control
  if daemonsets_enabled and state:
    api = kubernetes.client.AppsV1Api()
    try:
      if label_selector=='':
        api_response = api.list_namespaced_daemon_set(namespace=object_namespace)
      else:
        api_response = api.list_namespaced_daemon_set(namespace=object_namespace,label_selector=label_selector)
      logger.info ("Found %d daemonset to turn off",len(api_response.items))  
      for d in api_response.items:
        logger.debug("Daemonset %s has %s desired replicas", d.metadata.name,d.status.desired_number_scheduled)
        if d.status.desired_number_scheduled>0 :
          turn_off_daemonset(name=d.metadata.name,namespace=d.metadata.namespace,logger=logger,kopf=kopf,metadata=d.metadata,spec=d.spec,status=d.status,api=api,dry_run=dry_run,node_selector=node_selector)
    except ApiException as e:
      logger.error("Exception when calling AppsV1Api->list_namespaced_daemon_set: %s\n" % e)

  # Turning on state and deamonsets are under control
  if daemonsets_enabled and not state:
    api = kubernetes.client.AppsV1Api()
    try:
      if label_selector=='':
        api_response = api.list_namespaced_daemon_set(namespace=object_namespace)
      else:
        api_response = api.list_namespaced_daemon_set(namespace=object_namespace,label_selector=label_selector)
      logger.info ("Found %d daemonset to turn on",len(api_response.items))
      for d in api_response.items:
        logger.debug("Daemonset %s has %s desired replicas", d.metadata.name,d.status.desired_number_scheduled)
        if d.status.desired_number_scheduled==0 :
          turn_on_daemonset(name=d.metadata.name,namespace=d.metadata.namespace,logger=logger,kopf=kopf,metadata=d.metadata,spec=d.spec,status=d.status,api=api,dry_run=dry_run,node_selector=node_selector)
    except ApiException as e:
      logger.error("Exception when calling AppsV1Api->list_namespaced_daemon_set: %s\n" % e)


  # Turning off state and statefulset are under control
  if statefulsets_enabled and state:
    api = kubernetes.client.AppsV1Api()
    try:
      if label_selector=='':
        api_response = api.list_namespaced_stateful_set(namespace=object_namespace)
      else:
        api_response = api.list_namespaced_stateful_set(namespace=object_namespace,label_selector=label_selector)
        logger.info ("Found %d statefulset to turn off",len(api_response.items))
      for d in api_response.items:
        logger.debug("Statefulset %s has %s replicas", d.metadata.name,d.spec.replicas)
        if d.spec.replicas>0 :
          turn_off_statefulset(name=d.metadata.name,namespace=d.metadata.namespace,logger=logger,kopf=kopf,metadata=d.metadata,spec=d.spec,api=api,dry_run=dry_run)
    except ApiException as e:
      logger.error("Exception when calling AppsV1Api->list_namespaced_stateful_set: %s\n" % e)

  # Turning off state and statefulset are under controll
  if statefulsets_enabled and not state:
    api = kubernetes.client.AppsV1Api()
    try:
      if label_selector=='':
        api_response = api.list_namespaced_stateful_set(namespace=object_namespace)
      else:
        api_response = api.list_namespaced_stateful_set(namespace=object_namespace,label_selector=label_selector) 
        logger.info ("Found %d statefulset to turn on",len(api_response.items))
      for d in api_response.items:
        logger.debug("Statefulset %s has %s replicas", d.metadata.name,d.spec.replicas)
        if d.spec.replicas==0 :
          turn_on_statefulset(name=d.metadata.name,namespace=d.metadata.namespace,logger=logger,kopf=kopf,metadata=d.metadata,spec=d.spec,api=api,dry_run=dry_run)
    except ApiException as e:
      logger.error("Exception when calling AppsV1Api->list_namespaced_stateful_set: %s\n" % e)


@kopf.on.delete('djkormo.github', 'v1alpha1', 'shutdown')
def delete_shutdown_operator(spec, name, status, namespace, logger, **kwargs):
    logger.info(f"Deleting: {name} with {spec}")
    pass

# Operator logic end      


