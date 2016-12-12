Title: Docker 网络方案 Calico 新版上手体验 
Date: 2016-12-10
Category: others
Tags: docker, network, calico
Slug: docker-networking-calico
Author: X-Chu
Summary: docker networking calico vs macvlan


# 摘要

距离上次分享 Calico 已经过去快半年的时间了，Calico v2.0 也马上就要发布了，这次跟大家一起感受下新版，
简单总结下作为使用者我看到的 Calico 的变化，包括组件，文档和 `calicoctl` ，还有会和 MacVlan 做一下对比说明原理，最后总结下适合 Calico 的使用场景。

# Calico 简介回顾

### Calico 架构

Calico 是一个三层的数据中心网络方案，而且方便集成 OpenStack 这种 IaaS 云架构，能够提供高效可控的 VM、容器、裸机之间的通信。

![Calico Arch][calico_arch]
[calico_arch]: images/calico_arch.png "calico arch"

结合上面这张图，我们来过一遍 Calico 的核心组件：

- Felix，Calico agent，跑在每台需要运行 workload 的节点上，主要负责配置路由及 ACLs 等信息来确保 endpoint 的连通状态；
- etcd，分布式键值存储，主要负责网络元数据一致性，确保 Calico 网络状态的准确性；
- BGP Client(BIRD), 主要负责把 Felix 写入 kernel 的路由信息分发到当前 Calico 网络，确保 workload 间的通信的有效性；
- BGP Route Reflector(BIRD), 大规模部署时使用，摒弃所有节点互联的 mesh 模式，通过一个或者多个 BGP Route Reflector 来完成集中式的路由分发；

通过将整个互联网的可扩展 IP 网络原则压缩到数据中心级别，Calico 在每一个计算节点利用 Linux kernel 实现了一个高效的 vRouter 来负责数据转发
而每个 vRouter 通过 BGP 协议负责把自己上运行的 workload 的路由信息像整个 Calico 网络内传播 － 小规模部署可以直接互联，大规模下可通过指定的 BGP route reflector 来完成。

这样保证最终所有的 workload 之间的数据流量都是通过 IP 包的方式完成互联的。

![Calico ip-hops][calico_ip_hops]
[calico_ip_hops]: images/calico-ip-hops.png "calico ip hops"

Calico 节点组网可以直接利用数据中心的网络结构（支持 L2 或者 L3），不需要额外的 NAT，隧道或者 VXLAN overlay network。

![Calico no-encap][calico_no_encap]
[calico_no_encap]: images/calico-no-encap.png "calico no encap"

如上图所示，这样保证这个方案的简单可控，而且没有封包解包，节约 CPU 计算资源的同时，提高了整个网络的性能。

此外，Calico 基于 iptables 还提供了丰富而灵活的网络 policy, 保证通过各个节点上的 ACLs 来提供 workload 的多租户隔离、安全组以及其他可达性限制等功能。

更详细的介绍大家可以参考之前的分享：http://edgedef.com/docker-networking.html 或者 http://dockone.io/article/1489


# Calico CNI 及 Canal

Container Network Interface [CNI](https://github.com/containernetworking/cni) 容器网络 spec 是由 CoreOS 提出的，被 Mesos， Kubernetes 以及 rkt 等接受引入
使用。

Calico 在对 Docker 家的 CNM 和 libnetwork 提供更好的支持的同时，为了更亲和 Kubernetes 和 Mesos 等容器管理平台，也在积极的努力，所以不但有对 CNI 的支持，而且还和 CoreOS 一起组建了
新的公司 TiGERA（https://www.tigera.io/），主推 [Canal](https://github.com/tigera/canal) 将 Calico 的 policy 功能加入到 [Flannel](https://github.com/coreos/flannel) 的网络中，为和 k8s 的网络提供更好的 ACL 控制。

# Calico 的新版变化

接下来简单介绍下 Calico 新版带来了哪些变化[1]:

### 组件层面

先看一下 v2.0.0-rc2 中包含的组件列表:

v2.0.0-rc2
- felix	2.0.0-rc4
- calicoctl	v1.0.0-rc2
- calico/node	v1.0.0-rc2
- calico/cni	v1.5.3
- libcalico	v0.19.0
- libcalico-go	v1.0.0-rc4
- calico-bird	v0.2.0-rc1
- calico-bgp-daemon	v0.1.1-rc2
- libnetwork-plugin	v1.0.0-rc3
- calico/kube-policy-controller	v0.5.1
- networking-calico	889cfff

对比下 v1.5 或者之前的版本：

v1.5.0
- felix	v1.4.1b2
- calicoctl	v0.22.0
- calico/node	v0.22.0
- calico/node-libnetwork	v0.9.0
- calico/cni	v1.4.2
- libcalico	v0.17.0
- calico-bird	v0.1.0
- calico/kube-policy-controller	v0.3.0

可以看到组件层面 Calico 也发生了比较大的变化，其中新增：

- libcalico-go (Golang Calico library function, used by both `calicoctl`, `calico-cni` and `felix`)
- calico-bgp-daemon （GoBGP based Calico BGP Daemon，alternative to BIRD）
- libnetwork-plugin (Docker libnetwork plugin for Project Calico, integrated with the `calico/node` image)
- networking-calico （OpenStack/Neutron integration for Calico networking）

总结来看，就是组件语言栈转向 Golang，包括原来 Python 的 `calicoctl` 也用 Golang 重写了；同时面向使用者提供更好的扩展性和集成能力。

### 使用层面

#### 更好的文档和积极响应的 Slack：

- http://docs.projectcalico.org/v2.0/introduction/

开源软件的文档对于使用者来说很重要，Calico 的文档正在变的越来越好，尽量保证每种使用场景（docker，Mesos, CoreOS, K8s, OpenStack 等) 都能找到可用的参考。

除此之外，Calico 还维护了一个很快响应的 [Slack](https://slack.projectcalico.org/)，有问题可以随时到里边提问，这种交互对开源的使用者来说也是很好的体验。

#### 重新面向 Kubernetes 改写的 `calicoctl` UX 模型

毫无疑问，这是 Calico 为了更好的集成到 Kubernetes 所做出的努力和改变，也是对越来越多使用 k8s 同时又想尝试 Calico 网络的用户的好消息，这样大家就可以像在 k8s 中定义
资源模型一样通过 YAML 文件来定义 Calico 中的 Pool，Policy 这些模型了，同时也支持 label&selector 模式，保证了使用上的一致性。
具体的 Calico 定义资源模型的例子在后面的 Demo 中会有体现。


# Calico 组件原理 Demo

为了理解 Calico 工作原理，顺便体验新版 Calico，我们准备了两套 Demo 环境，一套是新版 Calico，另一套是对比环境 MacVlan。

Calico 以测试为目的集群搭建，步骤很简单，这里不展开了，
大家可以直接参考 http://docs.projectcalico.org/master/getting-started/docker/installation/manual

MacVlan 的集群搭建，步骤也相对简单,
参考：https://github.com/alfredhuang211/study-docker-doc/blob/master/docker%E8%B7%A8%E4%B8%BB%E6%9C%BAmacvlan%E7%BD%91%E7%BB%9C%E9%85%8D%E7%BD%AE.md

这里默认已经有了两套 Docker Demo 集群：
- Calico 网络的集群，分别是：10.1.1.103(calico01) 和 10.1.1.104(calico02)
- MacVlan 集群，分别是：10.1.1.105 和 10.1.1.106

### Demo 1: Calico 三层互联

calicoctl node status 截图：
![Calico status][calico_status]
[calico_status]: images/calico_v2_status.png "calico status"

同时，已经有 IP Pool 创建好，是：192.168.0.0/16

calicoctl get pool 截图：
![Calico pool][calico_pool]
[calico_pool]: images/calico_v2_pool_get.png "calico pool"

当前集群也已经通过使用 calico driver 和 IPAM 创建了不同的 docker network，本次 demo 只需要使用 net1

docker network ls 截图：
![Docker network][docker_network]
[docker_network]: images/calico_v2_docker_network.png "docker network"

calicoctl get profile 截图：
![Calico profile][calico_profile]
[calico_profile]: images/calico_v2_profile.png "calico profile"

下面我们使用 net1 这个网络，在两台机器上各启动一个容器：

在 calico01 上：

    docker run --net net1 --name workload-A -tid busybox

在 calico02 上：

    docker run --net net1 --name workload-B -tid busybox

容器连通性测试截图：

![ip connect 1][ip_connect_1]
[ip_connect_1]: images/calico_v2_ip_connect_1.png "ip connect 1"
![ip connect 2][ip_connect_2]
[ip_connect_2]: images/calico_v2_ip_connect_2.png "ip connect 2"


### Demo 2: MacVlan 二层互联

创建 MacVlan 网络，分别在两台主机上使用相同命令

    docker network create -d macvlan --subnet=192.168.1.0/24 --gateway=192.168.1.1 -o parent=enp0s3 -o macvlan_mode=bridge 192_1

创建容器：

10.1.1.105:

    docker run --net=192_1 --ip=192.168.1.168 -id --name test01 busybox sh

10.1.1.106:

    docker run --net=192_1 --ip=192.168.1.188 -id --name test11 busybox sh

测试网络连通性：

    docker exec test01 ping -c 4 192.168.1.188

![macvlan connect][macvlan_connect]
[macvlan_connect]: images/macvlan_connect.png "macvlan connect"

### Calico IP 路由实现及 Wireshark 抓包

![Calico data plane 1][calico_data_plane_1]
[calico_data_plane_1]: images/calico_data_plane_1.png "calico data plane 1"

根据上面这个 Calico 数据平面概念图，结合我们的例子，我们来看看 Calico 是如何实现跨主机互通的：

两台 slave route 截图：
![slave route 1][slave_route_1]
[slave_route_1]: images/calico_v2_route_slave_1.png "route slave 1"
![slave route 2][slave_route_2]
[slave_route_2]: images/calico_v2_route_slave_2.png "route slave 2"

对照两台主机的路由表，我们就知道，如果主机 1 上的容器想要发送数据到主机 2 上的容器，
那它就会 match 到响应的路由规则，将数据包转发给主机 2，那整个数据流就是：

    container -> calico01 -> one or more hops ->  calico02 -> container

最后，让我们来看看 Wireshark 抓包的截图对比：

Calico：
![wireshark calico][wireshark_calico]
[wireshark_calico]: images/calico_v2_ws.png "wireshark calico"
![wireshark calico container][wireshark_calico_container]
[wireshark_calico_container]: images/calico_v2_ws_container.png "wireshark calico container"

MacVlan：
![wireshark macvlan][wireshark_macvlan]
[wireshark_macvlan]: images/macvlan_ws.png "wireshark macvlan"

从上图对比中也能看出，不同于 MacVlan，Calico 网络中容器的通信是没有额外的 ARP 广播的，容器的数据包在节点之间使用的节点的 MAC 地址，这也是 Calico 作为三层方案的特点之一。
这同时也说明了，节点之间网络部分如果想对于容器间通信在二层做 filter 或者控制在 Calico 方案中是不起作用的。

这样，跨主机的 Calico 容期间三层通信就 Demo 完了，其他的 Calico 特性这里就一一介绍了，鼓励大家可以自己使用 VMs 搭起来亲自试试。

# Calico 使用场景

http://contiv.github.io

Contiv 是 Cisco 开源出来的针对容器的基础架构，主要功能是提供基于 Policy 的网络和存储管理，是面向微服务的一种新基架。

Contiv 能够和主流的容器编排系统整合，包括：Docker Swarm, Kubernetes, Mesos and Nomad。

![Contiv net][contiv_net]
[contiv_net]: images/contiv_net.png "contiv net"

如上图所示，Contiv 比较“诱人”的一点就是，它的网络管理能力，既有L2(vlan)、L3(BGP), 又有 Overlay(VxLAN), 
而且还能对接 Cisco 自家的 SDN 产品 ACI。可以说有了它就可以无视底层的网络基础架构，向上层容器提供一致的虚拟网络了。

### 二层网络

- 多租户网络混部在同一台主机上
- 集成现有 SDN 方案
- 能够和非容器环境兼容协作，不依赖物理网络具体细节
- 即时生效的容器网络 policy/ACL/QoS 规则

### 三层网络

### 对容器间通信二层数据包有分析和控制需求

# 总结

随着容器网络的发展，各家会越来越多的关注"落地"，相信后面各家都是在易用性、易维护性上继续努力，同时也一定会加大对各个容器编排方案的支持上。
回过头看 Calico 的新版本发展，也印证了这些要求：

- 易用性，兼容 k8s 的 calicoctl UX；
- 易维护性，Calico 本身为三层方案，而且Calico 能够兼容二层和三层的网络设计，可以和现有 DC 网络的整合和维护；
- 更好的和现有方案的集成，包括 OpenStack，CNI／Canal，Mesos 等，Calico 在网络方案的适用性方案还是很有竞争力的；

2016年很快结束了，作为容器网络的爱好者，个人希望在 2017 年看到真正成熟稳定的落地容器网络方案。

能力所限，全文中难免有错误，随时欢迎指正。谢谢！


[1]: https://www.projectcalico.org/celebrating-two-milestone-releases/ "Calico v2.0 Beta"
