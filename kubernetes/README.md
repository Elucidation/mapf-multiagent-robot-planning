# Kubernetes Cluster config folder

This folder contains the configuration scripts to start up a kubernetes cluster.

For local development one can use `minikube`


Create/Destroy the automated warehouse sim

```
kubectl create -f .\automated-warehouse-deploy-and-services.yaml
kubectl destroy -f .\automated-warehouse-deploy-and-services.yaml
```


Create/Destroy the automated warehouse web front end

```
kubectl create -f .\automated-warehouse-web-deploy-and-services.yaml
kubectl destroy -f .\automated-warehouse-web-deploy-and-services.yaml
```

*Note: Currently socket.io not working due to ingress rules WIP*


## Some extra commands for docker dev work (DEV)

```
docker run -w /home/app/ --rm -it -v C:/Users/sam/Documents/minikube_vols/mapf-multiagent-robot-planning:/home/app/mapf-multiagent-robot-planning --name aw_dev_alpine  alpine
```

```
docker run -w /home/app/ --rm -it -v vol1:/home/app --name aw_dev_alpine  alpine
```

Start redis server locally on docker

```
docker run --name redis-server -v vol-redis:/data -p 6379:6379 redis:alpine redis-server --save "60" "1" --loglevel warning
```

Mount Windows git dir to minikub (process has to stay alive)

```
minikube mount <windows-path>:/data/app
```

Running world sim locally with a specific DB path

```
python -m world_sim
```
