Title: Alluxio 小调 
Date: 2017-08-17
Category: bigdata
Tags: alluxio, hadoop, spark
Slug: alluxio-simple-test
Author: X-Chu
Summary: simple tests on Alluxio with HDFS


## 背景

### Alluxio 简介

![Alluxio stack][alluxio_stack]
[alluxio_stack]: images/alluxio/alluxio_stack.png "Alluxio stack(From: https://www.alluxio.com/docs/community/1.5/en/)"

Alluxio（之前名为Tachyon）是世界上第一个以内存为中心的虚拟的分布式存储系统。它统一了数据访问的方式，为上层计算框架和底层存储系统构建了桥梁。 应用只需要连接Alluxio即可访问存储在底层任意存储系统中的数据。此外，Alluxio的以内存为中心的架构使得数据的访问速度能比现有常规方案快几个数量级。

### Alluxio 架构及组件

![Alluxio arch][alluxio_arch]
[alluxio_arch]: images/alluxio/alluxio_arch.png "Alluxio arch(From: http://blog.iwantfind.com/archives/76)"

核心组件：

- Master： 主从，有高可用配置方案
- Worker：Alluxio的Worker负责管理分配给Alluxio的本地资源。这些资源可以是本地内存，SDD或者硬盘，其可以由用户配置。 Alluxio的Worker以块的形式存储数据，并通过读或创建数据块的方式处理来自Client读写数据的请求。但Worker只负责这些数据块上的数据；文件到块的实际映 射只会存储在Master上。
- Client：与Alluxio服务端交互的入口。它为用户暴露了一组文件系统API。Client通过发起与Master 的通信来执行元数据操作，并且通过与Worker通信来读取Alluxio上的数据或者向Alluxio上写数据。

### 关键功能：

- 灵活的文件API： Alluxio的本地API类似于java.io.File类，提供了 InputStream和OutputStream的接口和对内存映射I/O的高效支持。我们推荐使用这套API以获得Alluxio的最好性能。 另外，Alluxio提供兼容Hadoop的文件系统接口，Hadoop MapReduce和Spark可以使用Alluxio代替HDFS。
- 层次化存储：通过分层存储，Alluxio不仅可以管理内存，也可以管理SSD 和HDD,能够让更大的数据集存储在Alluxio上。数据在不同层之间自动被管理，保证热数据在更快的存储层上。自定义策 略可以方便地加入Alluxio，而且pin的概念允许用户直接控制数据的存放位置。
- 统一命名空间： Alluxio通过挂载功能在不同的存储系统之间实 现高效的数据管理。并且，透明命名在持久化这些对象到底层存储系统时可以保留这些对象的文件名和目录层次结构。

### 关键配置：

- alluxio.user.file.readtype.default CACHE_PROMOTE

    Default read type when creating Alluxio files. Valid options are `CACHE_PROMOTE` (move data to highest tier if already in Alluxio storage, write data into highest tier of local Alluxio if data needs to be read from under storage), `CACHE` (write data into highest tier of local Alluxio if data needs to be read from under storage), `NO_CACHE` (no data interaction with Alluxio, if the read is from Alluxio data migration or eviction will not occur).

- alluxio.user.file.writetype.default MUST_CACHE

    Default write type when creating Alluxio files. Valid options are `MUST_CACHE` (write will only go to Alluxio and must be stored in Alluxio), `CACHE_THROUGH` (try to cache, write to UnderFS synchronously), `THROUGH` (no cache, write to UnderFS synchronously).

## 快速验证

### 测试环境

本地 vm 搭建快速验证环境:

- Hadoop： 2.7.4
- Alluxio： 1.5.0-hadoop-2.7 (已经做好容器化：mirror.jd.com/pino/alluxio:1.5.0-hadoop-2.7)
- Spark: spark-2.2.0-hadoop2.7

### 测试场景

默认配置下的读（写）效率（readtype.default CACHE_PROMOTE，writetype.default MUST_CACHE）

通过 spark shell 测试 textfile + count 的耗时

#### 读取约 50/100/200M 文件，并进行 count：

- via HDFS: ~ 2/4.1/5.6 s

![50 count hdfs][50_count_hdfs]
[50_count_hdfs]: images/alluxio/50_count_hdfs.png "50M count hdfs"

![100 count hdfs][100_count_hdfs]
[100_count_hdfs]: images/alluxio/100_count_hdfs.png "100M count hdfs"

![200 count hdfs][200_count_hdfs]
[200_count_hdfs]: images/alluxio/200_count_hdfs.png "200M count hdfs"

- via Alluxio(In memory): ~ 0.2/0.8/0.8 s

![50 count][50_count]
[50_count]: images/alluxio/50_count.png "50M count"

![100 count][100_count]
[100_count]: images/alluxio/100_count.png "100M count"

![200 count][200_count]
[200_count]: images/alluxio/200_count.png "200M count"

#### 写入 约50/100 文件：

- via HDFS: ~ 2/13 s

![50 save hdfs][50_save_hdfs]
[50_save_hdfs]: images/alluxio/50_save_hdfs.png "50M save hdfs"

![100 save hdfs][100_save_hdfs]
[100_save_hdfs]: images/alluxio/100_save_hdfs.png "100M save hdfs"

- via Alluxio(writetype.default MUST_CACHE): 2/5 s

![50 save][50_save]
[50_save]: images/alluxio/50_save.png "50M save"

![100 save][100_save]
[100_save]: images/alluxio/100_save.png "100M save"


### 测试结论

- 对于读取：

| Size | HDFS Time Cost| Alluxio(In memory) Time Cost|
| --- | --- | --- |
| 50M | 2s | 0.2s| 
| 100M | 4s | 0.8s|
| 200M | 4s | 0.8s|

借助 Alluxio 的内存机制，对于已经在内存中的文件，后续操作都可以享受内存级别的读取速度，

文件越大优势越明显，文件反复使用的次数越多，优势越明显；

- 对于写入：

| Size | HDFS Time Cost| Alluxio(In memory) Time Cost|
| --- | --- | --- |
| 50M | 2s | 2s| 
| 100M | 13s | 5s|


根据配置的写入策略不同，效果不一样，具体的需要根据需求来调整。

针对目前（默认）写入策略，写入也是文件越大优势越明显；

对于后续还需要被使用的，写入 Alluxio 会提供后续读入时的加速效果。

## 可挖掘的价值点

- 加速数据读取和写入，如：HDFS；
- 搭建统一的文件接入层（HDFS，共享文件系统，本地硬盘）
- 借助 K8S 搭建统一的 Alluxio as a Service 的服务
- 结合 Spark 提供更快更稳当的实时处理能力

## 遗留工作

- 高可用集群化部署验证
- 和现有使用场景结合的成规模的验证（含网络 IO 监控，因为涉及跨节点通讯）
- 稳定性及规模测试
 
## 小结

根据目前了解的情况，可以认为 Alluxio 已经被比较大规模的应用，并证明其价值。

在共享内存和统一文件层接入这两个方面，都可以带来便利和性能提升，

而且并没有引入过多的改动和运维负担。


能力所限，文中难免有错误，随时欢迎指正。谢谢！

