# TestKCPTUN
A script for speedtest and get the best config of kcptun.

简单的python脚本用于测试获得[KCPTUN](https://github.com/xtaci/kcptun)的**最优**（带宽最大）配置。

## 依赖

1. Python3.6+. 请自行搜索如何安装（*nix系统应该都有自带的python3程序，但是有些可能是python3.5，不保证能正常运行，或许可用）；

2. OS: OSX/Linux，如果是windows建议用WSL

3. python包paramiko：

   ```shell
   pip3 install paramiko --user
   ```

4. iperf3，服务器和本地都需要安装

   ```shell
   # for ubuntu
   sudo apt install iperf3
   ```

5. 将服务器设置为免密码登录方式（**请在自己的计算机上执行本操作，非个人计算机请勿执行**）

   首先看本机上有没有ssh-key

   ```shell
   ls ~/.ssh/id_rsa.pub
   ```

   如果没有这个文件（有可以跳过这一步），运行

   ```shell
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   ```

   中间一直按回车即可；

   将本机ssh-key发送到服务器

   ```shell
   ssh-copy-id -i ~/.ssh/id_rsa.pub user@host
   ```

   一般来说会需要输入服务器的密码，输入即可。

6. 本机下载了kcptun客户端，远程服务器下载有kcptun服务端

## 使用

1. 在文件`autokcp.py`中的这个位置，填入对应的信息

   ```python
   ####################  Modify here  ####################
   # hostname Examples:
   # IPv4:
   #     hostname = '192.168.0.1'
   # IPv6:
   #     hostname = 'ff08::1'
   hostname = '192.168.0.1'
   port = 22
   username = 'root'
   pathKcptunServer = '/root/kcptun/server_linux_amd64'
   pathKcptunClient = './client_linux_amd64'
   pathOutJsonFile = './log.json'
   portKcptunServer = '9990'
   portKcptunClient = '9469'
   setConfig = {
       'crypt': 'aes',
       'nocomp':'',
       'mode': 'fast2',
       'quiet': '',
       'smuxver': '2'
   }
   optionList = [
       'sockbuf',
       'smuxbuf'
   ]
   #######################################################
   ```

   各个参数的意义：

   - `hostname`：服务器IP地址，支持IPv4和IPv6（IPv6地址不用加中括号）
   - `port`：ssh登录端口，一般默认即可
   - `username`：ssh用户名，默认是`root`
   - `pathKcptunServer`：服务器端kcptun程序的位置（建议用绝对路径）
   - `pathKcptunClient`：客户端kcptun程序的位置（建议用绝对路径）
   - `pathOutJsonFile`：测速结果输出文件（请确保是`.json`格式）
   - `portKcptunServer`：服务端kcptun监听端口，如果没冲突默认即可
   - `portKcptunClient`：客户端kcptun监听端口，如果没冲突默认即可
   - `setconfig`：设定部分固定不需要改的配置
   - `optionList`：添加需要搜索的选项

2. 在远端服务器上运行iperf3

   ```shell
   iperf3 -s
   ```

   （这个出于监控考虑所以没有在本地启动）

3. 在本地运行命令，测试一下服务器iperf3是否正常

   ```shell
   iperf3 -c hostname
   ```

   如果有问题请自行Baidu/Google查询

4. 运行脚本

   ```shell
   python3 autokcp.py run
   ```

5. 等待结果

## 其他

1. 脚本运行时间取决于搜索的参数选项数量，示例中搜索了`smuxbuf`和`sockbuf`，总搜索次数=3\*3=9，运行时间=9\*10=90s，还是需要比较多时间的，所以建议一次不要同时搜索太多参数；

2. 脚本运行中如果出错了，或者是人为中断后，请运行以下命令以清理进程

   ```shell
   python3 autokcp.py clean
   ```

## 使用示例

1. 固定其他配置，搜索不同加密方式对于速度的影响

   ```python
   setConfig = {
       'nocomp':'',
       'mode': 'fast2',
       'quiet': ''
   }
   optionList = [
       'crypt'
   ]
   ```

   运行脚本，等待运行结束后，结果如下

   ```shell
   -l [::]:9990 -t [::1]:5201 --nocomp  --mode fast2 --quiet  --smuxver 1 --smuxbuf 4194304 --crypt tea
   Download: 11.1Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --mode fast2 --quiet  --smuxver 1 --smuxbuf 4194304 --crypt twofish
   Download: 10.9Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --mode fast2 --quiet  --smuxver 1 --smuxbuf 4194304 --crypt xor
   Download: 10.0Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --mode fast2 --quiet  --smuxver 1 --smuxbuf 4194304 --crypt aes-192
   Download: 9.9Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --mode fast2 --quiet  --smuxver 1 --smuxbuf 4194304 --crypt 3des
   Download: 9.7Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --mode fast2 --quiet  --smuxver 1 --smuxbuf 4194304 --crypt aes-128
   Download: 9.2Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --mode fast2 --quiet  --smuxver 1 --smuxbuf 4194304 --crypt cast5
   Download: 8.9Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --mode fast2 --quiet  --smuxver 1 --smuxbuf 4194304 --crypt blowfish
   Download: 8.9Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --mode fast2 --quiet  --smuxver 1 --smuxbuf 4194304 --crypt salsa20
   Download: 8.7Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --mode fast2 --quiet  --smuxver 1 --smuxbuf 4194304 --crypt xtea
   Download: 8.7Mbits/sec
   ```

2. 固定其他配置，搜索不同`mode`对于速度的影响

   ```python
   setConfig = {
       'nocomp':'',
       'quiet': ''
   }
   optionList = [
       'mode'
   ]
   ```

   运行脚本，等待运行结束后，结果如下

   ```shell
   -l [::]:9990 -t [::1]:5201 --nocomp  --quiet  --smuxver 1 --smuxbuf 4194304 --mode fast3
   Download: 7.5Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --quiet  --smuxver 1 --smuxbuf 4194304 --mode fast
   Download: 7.5Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --quiet  --smuxver 1 --smuxbuf 4194304 --mode fast2
   Download: 7.3Mbits/sec
   -l [::]:9990 -t [::1]:5201 --nocomp  --quiet  --smuxver 1 --smuxbuf 4194304 --mode normal
   Download: 6.3Mbits/sec
   ```

   

