Title: Docker 网络方案初探 
Date: 2016-06-26
Category: others
Tags: docker, network, calico
Slug: docker-networking
Author: X-Chu
Summary: docker networking calico vs contiv


# 摘要

随着容器的火热发展，大家对容器的网络特性要求也开始越来越高，比如：

- 一容器一IP
- 多主机网络
- 网络隔离
- ACL
- 对接 SDN 等等

这次主要跟大家聊聊 Docker 的网络方案，主要包括现有容器网络方案介绍，
接下来重点讲解 Calico 的特性及技术点，作为引申和对比再介绍下 Contiv 的特性,
最后给出对比测试结果。

# 现有的主要 Docker 网络方案

首先简单介绍下现有的容器网络方案，网上也看了好多对比，大家之前都是基于实现方式来分，

### 隧道方案

通过隧道, 或者说 overlay network 的方式：

- Weave，UDP 广播，本机建立新的 BR，通过 PCAP 互通。
- Open vSwitch(OVS)，基于 VxLAN 和 GRE 协议，但是性能方面损失比较严重。
- Flannel，UDP 广播，VxLan。

隧道方案在 IaaS 层的网络中应用也比较多，大家共识是随着节点规模的增长复杂度会提升，
而且出了网络问题跟踪起来比较麻烦，大规模集群情况下这是需要考虑的一个点。

### 路由方案

还有另外一类方式是通过路由来实现，比较典型的代表有：

- Calico，基于 BGP 协议的路由方案，支持很细致的 ACL 控制，对混合云亲和度比较高。
- Macvlan，从逻辑和 Kernel 层来看隔离性和性能最优的方案，基于二层隔离，所以需要二层路由器支持，大多数云服务商不支持，所以混合云上比较难以实现。

路由方案一般是从 3 层或者 2 层实现隔离和跨主机容器互通的，出了问题也很容易排查。

我觉得以后再讨论容器网络方案，不仅要看实现方式，而且还要看网络模型的“站队”，比如说你到底是要用 Docker 原生的 “CNM”，还是谷歌, CoreOS 主推的 “CNI”。

### Docker libnetwork Container Network Model (CNM) 阵营

- Docker Swarm overlay
- Macvlan & IP network drivers
- Calico 
- Contiv (from Cisco)

Docker libnetwork 的优势就是原生，而且和 Docker 容器生命周期结合紧密；缺点也也可以理解为是原生，被 Docker “绑架”。

### Container Network Interface (CNI) 阵营

- Kubernetes
- Weave
- Macvlan
- Flannel
- Calico
- Contiv
- Mesos CNI

CNI 的优势是兼容其他容器技术(e.g. rkt)及上层编排系统(K8s & Mesos)，而且社区活跃，Kubernetes 加上 CoreOS主推；缺点是不是 Docker 原生。

而且从上的也可以看出，有一些第三方的网络方案是“脚踏两只船”的，
我个人认为目前这个状态下也是合情理的事儿，但是长期来看是存在风险的, 或者被淘汰，或者被收购。


# Calico

接下来重点介绍 Calico，原因是它在 CNM 和 CNI 两大阵营都扮演着比较重要的角色。即有着不俗的性能表现，提供了很好的隔离性，而且还有不错的 ACL 控制能力。

Calico 是一个纯3层的数据中心网络方案，而且无缝集成像 OpenStack 这种 IaaS 云架构，能够提供可控的 VM、容器、裸机之间的 IP 通信。

通过将整个互联网的可扩展 IP 网络原则压缩到数据中心级别，Calico 在每一个计算节点利用 Linux kernel 实现了一个高效的 vRouter 来负责数据转发，而每个 vRouter 通过 BGP 协议负责把自己上运行的 workload 的路由信息像整个 Calico 网络内传播 － 小规模部署可以直接互联，大规模下可通过指定的 BGP route reflector来完成。

这样保证最终所有的 workload 之间的数据流量都是通过 IP 路由的方式完成互联的。

![Calico ip-hops][calico_ip_hops]
[calico_ip_hops]: images/calico-ip-hops.png "calico ip hops"

Calico 节点组网可以直接利用数据中心的网络结构（无论是 L2 或者 L3），不需要额外的 NAT，隧道或者 overlay network。

![Calico no-encap][calico_no_encap]
[calico_no_encap]: images/calico-no-encap.png "calico no encap"

如上图所示，这样保证这个方案的简单可控，而且没有封包解包，节约 CPU 计算资源的同时，提高了整个网络的性能。

此外，Calico 基于 iptables 还提供了丰富而灵活的网络 policy, 保证通过各个节点上的 ACLs 来提供 workload 的多租户隔离、安全组以及其他可达性限制等功能。

### Calico 架构

![Calico Arch][calico_arch]
[calico_arch]: images/calico_arch.png "calico arch"

结合上面这张图，我们来过一遍 Calico 的核心组件：

- Felix，Calico agent，跑在每台需要运行 workload 的节点上，主要负责配置路由及 ACLs等信息来确保 endpoint 的连通状态；
- etcd，分布式键值存储，主要负责网络元数据一致性，确保 Calico 网络状态的准确性；
- BGP Client(BIRD), 主要负责把 Felix 写入 kernel 的路由信息分发到当前 Calico 网络，确保 workload 间的通信的有效性；
- BGP Route Reflector(BIRD), 大规模部署时使用，摒弃所有节点互联的 mesh 模式，通过一个或者多个 BGP Route Reflector 来完成集中式的路由分发；

### Calico Docker network 核心概念

从这里开始我们将“站队” CNM, 通过 Calico Docker libnetwork plugin 的方式来体验和讨论 Calico 容器网络方案。

先来看一下 CNM 模型：

![CNM Model][cnm_model]
[cnm_model]: images/cnm-model.jpg "cnm model"

从上图可以知道，CNM 基于3个主要概念：

- Sandbox，包含容器网络栈的配置，包括 interface，路由表及 DNS配置，对应的实现如：Linux Network Namespace；一个 Sandbox 可以包含多个 Network；
- Endpoint，做为 Sandbox 接入 Network 的介质，对应的实现如：veth pair，TAP；一个 Endpoint 只能属于一个 Network，也只能属于一个 Sandbox；
- Network，一组可以相互通信的 Endpoints；对应的实现如：Linux bridge，VLAN；Network 有大量 Endpoint 资源组成；

除此之外，CNM 还需要依赖另外两个关键的对象来完成 Docker 的网络管理功能，他们分别是：

- NetworkController, 对外提供分配及管理网络的 APIs，Docker libnetwork 支持多个活动的网络 driver，NetworkController 允许绑定特定的 driver 到指定的网络；
- Driver，网络驱动对用户而言是不直接交互的，它通过插件式的接入来提供最终网络功能的实现；Driver(包括 IPAM) 负责一个 network 的管理，包括资源分配和回收；

有了这些关键的概念和对象，配合 Docker 的生命周期，通过 APIs 就能完成管理容器网络的功能，具体的步骤和实现细节这里不展开讨论了，
有兴趣的可以移步 Github： https://github.com/docker/libnetwork/blob/master/docs/design.md

接下来再介绍两个 Calico 的概念：

#### Pool

#### Profile

### Demo

基于上面的架构及核心概念，我们先看一个简单的例子，直观的感受下 Calico 的网络管理。

### 数据层 & 控制层

![Calico data plane 1][calico_data_plane_1]
[calico_data_plane_1]: images/calico_data_plane_1.png "calico data plane 1"

![Calico data plane 2][calico_data_plane_2]
[calico_data_plane_2]: images/calico_data_plane_2.png "calico data plane 2"

### 安全策略 ACL


# Contiv

http://contiv.github.io

Contiv 是 Cisco 开源出来的针对容器的基础架构，主要功能是提供基于 Policy 的网络和存储管理，是面向微服务的一种新基架。

Contiv 能够和主流的容器编排系统整合，包括：Docker Swarm, Kubernetes, Mesos and Nomad。

![Contiv net][contiv_net]
[contiv_net]: images/contiv_net.png "contiv net"

如上图所示，Contiv 比较“诱人”的一点就是，它的网络管理能力，既有L2(vlan)、L3(BGP), 又有 Overlay(VxLAN), 
而且还能对接 Cisco 的 SDN 产品 ACI。可以说有了它就可以无视底层的网络基础架构，向上层容器提供一致的虚拟网络了。

### Contiv netplugin 特性

- 多租户网络混部在同一台主机上
- 集成现有 SDN 方案
- 能够和非容器环境兼容协作，不依赖物理网络具体细节
- 即时生效的容器网络 policy/ACL/QoS 规则

# 性能对比测试

最后附上我们使用 qperf 做的简单性能测试结果，我们选取了 vm-to-vm, host, calico-bgp, calico-ipip 以及 swarm overlay 进行了对比。

测试环境：VirtualBox VMs，OS：Centos 7.2，kernel 3.10，1 vCPU，1G Mem。

带宽对比结果如下：

![bw][bw]
[bw]: images/bw.png "bandwidth compare"

时延对比结果如下：

![lat][lat]
[lat]: images/lat.png "latency compare"

qperf 命令：

    # server 端
    $ qperf
    # client 端
    # 持续10s发送64k数据包，tcp_bw表示带宽，tcp_lat表示延迟
    $ qperf -m 64K -t 10 192.168.2.10 tcp_bw tcp_lat; client端，持续10s发送64k数据包，tcp_bw表示带宽，tcp_lat表示延迟
    # 从1开始指数递增数据包大小
    $ qperf -oo msg_size:1:64k:*2 192.168.2.10 tcp_bw tcp_lat； client端，从1开始指数递增数据包大小
