---
title: Raspberry Pi 5 初期設定
tags:
  - RaspberryPi
  - 初期設定
  - raspberrypi5
private: false
updated_at: '2026-09-02T12:47:44+09:00'
id: e1e5d5dc95c4649153f5
organization_url_name: null
slide: false
ignorePublish: false
posting_campaign_uuid: null
agreed_posting_campaign_term: false
---
Raspberry Pi 5 を最近購入しました。
初期セットアップ方法はバージョンによって少しずつ変わるため、2025年時点でのセットアップ手順をまとめます。

本記事では

-  OSイメージの作成
- Raspberry Pi の起動
- SSH 接続

までを扱います。

:::note info
**環境**
- マシン : RaspberryPi 5 (8GB)

- OS：Raspberry Pi OS (64bit)
    - Debian GNU/Linux 13 (trixie)  
    - Version: 13.1
- メモリ : SSD (960GB)
:::

# 目次
1. [OSイメージの作成](https://qiita.com/live_in_2107/items/e1e5d5dc95c4649153f5#1-os%E3%82%A4%E3%83%A1%E3%83%BC%E3%82%B8%E3%81%AE%E4%BD%9C%E6%88%90)
2. [起動](https://qiita.com/live_in_2107/items/e1e5d5dc95c4649153f5#2-%E8%B5%B7%E5%8B%95%E3%81%99%E3%82%8B)
3. [ipアドレスの確認](https://qiita.com/live_in_2107/items/e1e5d5dc95c4649153f5#3-ip%E3%82%A2%E3%83%89%E3%83%AC%E3%82%B9%E3%81%AE%E7%A2%BA%E8%AA%8D)
4. [パッケージ更新](https://qiita.com/live_in_2107/items/e1e5d5dc95c4649153f5#4-%E3%83%91%E3%83%83%E3%82%B1%E3%83%BC%E3%82%B8%E6%9B%B4%E6%96%B0)
5. [ssh接続を許可](https://qiita.com/live_in_2107/items/e1e5d5dc95c4649153f5#5-ssh%E6%8E%A5%E7%B6%9A%E3%82%92%E8%A8%B1%E5%8F%AF)

付録 : [USBの再利用](https://qiita.com/live_in_2107/items/e1e5d5dc95c4649153f5#%E4%BB%98%E9%8C%B2usb%E3%81%AE%E5%86%8D%E5%88%A9%E7%94%A8)
## 1. OSイメージの作成
Raspberry Pi は、ノートPCとは異なり、標準ではストレージが付属しておらず、OSは自分で準備する必要があります。
今回は、OSのインストールをRaspberry Pi Imagerを使用して行います。
<details><summary>Raspberry Pi Imagerについて</summary>

- ラズパイOSを簡単にmicro SDカードやUSBメモリにインストールができるアプリケーション
    - Windows版、Mac版、 Debian, Ubuntu (x86_64)版が用意されている
- Wi-Fiの登録など細かい設定も事前に済ませることができる

</details>

### 1-1. OSイメージ作成の準備
- 物品の用意を用意
    - PC (Raspberry Piとは別) <- M2 MacBookAirを使用
    - メモリ (microSDカードやUSBメモリ、SSDなど)
:::note info

**メモリのフォーマット**
メモリを初期化し、余計なファイルを削除することでインストールしています。
個人的にはCLIで毎回フォーマットを行ってます。

<details><summary>フォーマットの種類</summary>


| 規格       | 特徴                    | 最大サイズ |
| -------- | --------------------- | ----- |
| ExFAT    | OS依存の少ない汎用的な規格        | 制限なし  |
| **NTFS** | Windows向け（Macは読み取りのみ） | 制限なし  |
| FAT32    | 広く使われる規格              | 4GBまで |


</details>


```bash:terminal
$ diskutil list # 記憶領域の一覧表示
/dev/disk0 (internal, physical):
   ~~~
/dev/disk4 (external, physical):　<- 物理的に外部から入力していることがわかる
   #:                       TYPE NAME                    SIZE       IDENTIFIER
   0:      GUID_partition_scheme                        *63.9 GB    disk4
   1:                        EFI NO NAME                 209.7 MB   disk4s1
   2:       Microsoft Basic Data microSD                 63.7 GB    disk4s2
   
$ diskutil eraseDisk ExFAT microSD /dev/disk4 # 初期化 & フォーマット
```
この場合、`/dev/disk4`を`ExFAT`という形式のフォーマットを行う
`microSD` については、finderやエクスプローラーで表示する名前になります

:::
:::note alert

- 自分が指定した /dev/disk* 以外を削除するとデータが消えます。
- よく`diskutil list`コマンドで確認してください。

:::

-  PCにRaspberry Pi Imagerをインストール
    - [公式サイト](https://www.raspberrypi.com/software/)からダウンロードする

### 1-2. OSイメージの書き込み
起動後すると「ラズパイのシリーズ」「OS」「ストレージ」の選択を求められます。

※ 追加でWi-Fiの設定をする場合、「設定を編集する」を行う
![image.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/3113943/e427192a-83d3-49ae-be3a-308cecd525fc.png)

## 2. 起動する
- OSイメージの書き込みが完了したら、Raspberry Piに接続
起動時にpower supplyなど電源関連の問題で起動しない場合は、Raspberry Pi用の5.1V出力の電源を使用するとうまくできました。
作業机のドッキングステーション経由で給電していたので、出力電圧がラズパイの対応電圧とマッチしなかった可能性がありそうです。
参考資料 : [Raspberry Pi 5の電源について](https://note.com/catamua/n/n4756ec5788bf)
- 起動後、ユーザ名とパスワードを入力

## 3. ipアドレスの確認
- `ip a`コマンドで確認
```bash:ラズパイ
$ ip a
1: lo: ~~~

# 有線LAN
2: eth0: ~~~ 
    inet XXX.XXX.XXX.XXX/24 # ここがIPアドレス
    inet6 XXXX::XXXX:XXXX:XXXX/64 # IPv6用のIPアドレス

# 無線LAN
3: wlan0: ~~~
    inet XXX.XXX.XXX.XXX/24 # ここがIPアドレス
    inet6 XXXX::XXXX:XXXX:XXXX/64 # IPv6のIPアドレス

```

## 4. パッケージ更新

```bash
$ sudo apt-get upgrade
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
Calculating upgrade... Done
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
$ sudo reboot # 更新することをおすすめします。
```

## 5. ssh接続を許可
- `sudo raspi-config` で設定画面を開く
    
    ![スクリーンショット 2025-11-05 22.17.21.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/3113943/1d350020-78c5-46c7-a067-40e740a3687a.png)
- 「3 Interface Options」-> 「I1 SSH」と進む
    以下のような画面が開くので「\<Yes\>」を選択する。
    ![image.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/3113943/e583a5b7-5bc6-454d-89da-1eb08289ba5f.png)

### sshの確認
- sshの起動の確認
```bash
$ systemctl status ssh
🟢 ssh.service - OpenBSD Secure Shell server
     Loaded: loaded (/usr/lib/systemd/system/ssh.service; enabled; preset: enabled)
     Active: active (running) since Wed 2025-11-05 19:05:26 JST; 3h 33min ago
 Invocation: 3b13a7794e084a5083477cc49e129f19
       Docs: man:sshd(8)
             man:sshd_config(5)
   Main PID: 1009 (sshd)
      Tasks: 1 (limit: 9575)
        CPU: 188ms
     CGroup: /system.slice/ssh.service
             └─1009 "sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups"
```
`active`や`enable`と書かれていると起動しています。

- 22ポートの確認
```bash
$ sudo ss -tlnp | grep :22
LISTEN 0      128          0.0.0.0:22       0.0.0.0:*
LISTEN 0      128             [::]:22          [::]:*
```

以上で、sshできる状態になると思います。
以下のようにsshが実行できれば完了です。

```:クライアント
$ ssh <Host Name>@<IP address>
Linux raspberrypi 6.12.47+rpt-rpi-2712 #1 SMP PREEMPT Debian 1:6.12.47-1+rpt1 (YYYY-MM-DD) aarch64

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Last login: Sun month day :mm:ss YYYY from XXX.XXX.XXX.XXX

```

## 参考資料
https://www.raspberrypi.com/

https://note.com/catamua/n/n4756ec5788bf

https://note.com/rasen/n/ne52d4103bf9b#4WEMA

## 付録:USBの再利用
OSのインストールに使用したメモリを他の手段に利用するために初期化 & クリーンアップします。
やり方は、メモリを用意したときの手順と同じです。
```bash
$ diskutil list # 記憶領域の確認
    ~~~

$ diskutil eraseDisk ExFAT MEMOR /dev/disk4
    ~~~
    Mounting disk
    Finished erase on disk4

```


このコマンドが完了するとメモリは初期化され、通常のデータ保存用として使えるようになります
`/Volumes`でも認識されます
```
$ ls /Volumes 
Macintosh HD	MEMORY
```
