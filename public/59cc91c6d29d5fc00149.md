---
title: UbuntuをUSBでPCにインストールする in CLI!
tags:
  - Linux
  - Ubuntu
  - セットアップ
  - Ubuntu24.04
private: false
updated_at: '2025-07-02T17:33:19+09:00'
id: 59cc91c6d29d5fc00149
organization_url_name: null
slide: false
ignorePublish: false
posting_campaign_uuid: f6e320c01779cc1df58f
agreed_posting_campaign_term: true
---
本記事では、USBメモリを使用してUbuntuインストールする際の手順を、**CLI(コマンドラインインターフェース)**を中心に解説します。
### 話す内容
- USBメモリによるUbuntuインストールまでの流れ
- USBメモリの作成方法
- USBメモリの再利用の方法

### 話さない内容
- Ubuntuの細かいインストールの手続き
- WindowsからUbuntuをインストールするまでの失敗談
    - 後日別の記事で紹介したいと思います
- GUIツールとの比較
    - CLIでの処理についてのみ掲載しています
    - 参考までにRufusやbalenaEtcherなどのGUIツールでも同様の内容ができます
## 準備
Ubuntuのインストール用USBメモリを作成するために、以下のものを用意しましょう
- USBメモリ
    - 8GB以上の容量を推奨します(今回は512GBのメモリを使用します)
    - Ubuntuのインストールに必要なファイルを保存するため、使用するUSBメモリ内のデータを空の状態にしてください
    - すべて削除されてしまうため事前にバックアップをとり、中身が空の状態にしておくことを勧めます
- PC(CLI操作が行えるもの)
    - 本記事では、M2 Mac Book を使用して作業を行います
    - Windows PCでも同様の手順でCLI(WSLやGit Bashなど)から操作できます
- インターネット環境
    - UbuntuのISOイメージファイルをダウンロードする際に使用します

## 1. USB作成
UbuntuのOSイメージをUSBメモリに書き込み、インストール可能なUSBメモリを作成します
### 1-1. PCにUSBを指し、認識することを確認する
- USBメモリをPCに差し込み、正しく認識しているかを確認します

:::note warn
注意!
ここで誤ったディスク（内蔵SSDなど）を指定するとデータが消失します。  
必ず `diskutil list` でUSBメモリの識別子（例: `/dev/disk4`）を確認してください。

:::

- Macの場合
```bash
$ diskutil list
```
- このコマンドでは、現在PCに接続されているすべてのディスク(ドライブ)の一覧を表示します

```bash
/dev/disk0 (internal, physical):
   #:                       TYPE NAME                    SIZE       IDENTIFIER
   0:      GUID_partition_scheme                        *500.3 GB   disk0
   1:             Apple_APFS_ISC Container disk1         524.3 MB   disk0s1
   2:                 Apple_APFS Container disk3         494.4 GB   disk0s2
   3:        Apple_APFS_Recovery Container disk2         5.4 GB     disk0s3

/dev/disk3 (synthesized):
   #:                       TYPE NAME                    SIZE       IDENTIFIER
   0:      APFS Container Scheme -                      +494.4 GB   disk3
                                 Physical Store disk0s2
   1:                APFS Volume Macintosh HD            11.3 GB    disk3s1
   2:              APFS Snapshot com.apple.os.update-... 11.3 GB    disk3s1s1
   3:                APFS Volume Preboot                 7.2 GB     disk3s2
   4:                APFS Volume Recovery                1.0 GB     disk3s3
   5:                APFS Volume Data                    433.4 GB   disk3s5
   6:                APFS Volume VM                      24.6 KB    disk3s6

/dev/disk4 (external, physical):
   #:                       TYPE NAME                    SIZE       IDENTIFIER
   0:     FDisk_partition_scheme                        *512.1 GB   disk4
   1:               Windows_NTFS SSD-1                   512.1 GB   disk4s1
```

- 以上の結果より、`/dev/disk4`がUSBメモリ(`external, physical`)と表示され、サイズも接続したUSBメモリの容量と一致していることがわかります
- このコマンドの出力はPCの構成によって異なるため、必ずご自身の環境でUSBメモリの識別子(例:`/dev/disk4`)を確認してください
- また、Mac BookなどのLinuxのファイルシステムでは、`/Volumes/`配下にUSBメモリなどのメモリが認識されます
```bash
$ ls /Volumes 
Macintosh HD	USBMEMORY
```
- 今回は`/dev/diskX`の形式で直接指定して書き込みを行います

### 1-2. PCにUbuntuのOSデータをダウンロードします
- Ubuntuのインストールに必要なISOイメージファイルをダウンロードします。ISOファイルはOSのインストールに必要なデータがすべて詰まったイメージファイルです。
- 今回はUbuntuの最新の長期サポート版(LTS:Long Term Support)である`Ubuntu 24.04.2 Desktop(AMD64) LTS`をダウンロードします
- 細かいバージョンやCPUのアーキテクチャについては、以下の公式サイトから確認してください
    - [公式サイト:Ubuntuを入手する](https://jp.ubuntu.com/download)
    - 2025年7月1日時点の場合
    
    |名称|ダウンロードリンク|
    |---|---------------|
    |Ubuntu Desktop|`https://releases.ubuntu.com/24.04/ubuntu-24.04.2-desktop-amd64.iso`|
    | Ubuntu Server|`https://releases.ubuntu.com/24.04.2/ubuntu-24.04.2-live-server-amd64.iso`|
    
- 今回は、Ubuntu DesktopのISOファイルをダウンロードします
    - Downloadディレクトリにおくことをおすすめします
```bash
$ cd ~/Downloads
$ curl -LO https://releases.ubuntu.com/24.04/ubuntu-24.04.2-desktop-amd64.iso
```
- このコマンドを実行すると、`ubuntu-24.04.2-desktop-amd64.iso`というファイルが現在のディレクトリにダウンロードされます。ファイルサイズが6GBほどあるため、完了まで少々お待ち下さい
:::note info
- 完了後、確認として以下の作業を行うと安心かもしれません
    - ここでは、ダウンロードしたファイル`.iso`が正確であるか（破損や改ざんがないか）をチェックし、セキュリティと信頼性のための処理を行っています
```bash
$ curl -LO https://releases.ubuntu.com/24.04/SHA256SUMS

$ sha256sum -c SHA256SUMS 2>&1 | grep ubuntu-24.04.2-desktop-amd64.iso

ubuntu-24.04.2-desktop-amd64.iso: OK
```
- `ubuntu-24.04.2-desktop-amd64.iso: OK`となれば、問題ないことが確認できます
- `FAILED`と表示された場合は、再度ダウンロードすることをオススメします
:::

### 1-3. USBメモリのアンマウント
- ISOイメージをUSBメモリに書き込む前にアンマウントします
    - アンマウント
        - OSがディスクへの読み書きを停止し、安全に取り外し可能な状態にします
    - これにより、書き込み中の予期せぬエラーを防ぎます
- 手順1-1で確認した自身のUSBメモリの識別子(例:`/dev/disk4`)を指定して下さい
```bash
$ diskutil unmountDisk /dev/disk4
```
- 成功すると、`Unmount of all volumes on disk4 was successful`と表示されます

### 1-4. USBメモリへの書き込み
- いよいよUSBメモリへダウンロードしたISOイメージを書き込みます
- この操作では、USBメモリ内の既存のデータをすべて消去し、Ubuntuの起動可能なシステムを構築します
- このコマンドを間違ったディスクに指定するとシステム全体が破損する恐れがあるため、再度ご自身のUSBメモリの識別子が正しいことを確認してください
:::note info
- 補足
    - Macでは、`/dev/diskX`ではなく、`/dev/rdiskX`を使用すると、より高速に書き込みができます
    - `rdisk`とは、 raw disk modeを意味し、バッファリングを最小限に抑えることで書き込み速度を向上させます
:::

```bash
$ sudo dd if=ubuntu-24.04.2-desktop-amd64.iso of=/dev/rdisk4 bs=4m status=progress
$ sync  # 書き込みキャッシュを全てディスクへ反映
```
<details><summary>コマンドの解説</summary>

|コマンド|解説|
|------|----|
|`sudo`|管理者権限で実行する|
|`dd`|ファイルを変換・コピーする|
|`if=ubuntu-24.04.2-desktop-amd64.iso`|入力ファイルの指定|
|`of=/dev/rdisk4`|出力先の選択|
|`bs=4m`|ブロックサイズの指定(今回は4MBに設定します)|
|`status=progress`|書き込みの進行状況をリアルタイムに表示|

</details>

- このコマンドも少々時間がかかるため、完了を待ちましょう

### 1-5. USBメモリを取り外す前に
- `dd`コマンドが完了後、すぐにUSBメモリを抜き出してはいけません
- 書き込み操作が完全にディスクに反映されるまでには時間がかかる場合があります。
- 安全に取り外すために、以下のコマンドでUSBメモリをイジェクトします
```bash
$ diskutil eject /dev/disk4
```
- 成功すると`Disk /dev/disk4 ejected`が表示され、安全に取り外すことができます
- これでUbuntuのインストール用USBメモリの作成は完了です

## 2. Ubuntuのインストール
- 作成したUSBメモリを使用して、PCにUbuntuをインストールします

### 2-1. BIOS起動画面を開く
- UbuntuをインストールしたいPCに、作成したUSBメモリを差し込みます
- 使用しているメーカーの指示に従い、Boot MenuといったBIOS起動画面を開いて下さい
    - 一般的には`F2,F10, F12, Del(Delete), Esc`が使われます
    - 起動時ロゴが表示されたらすぐキーを押してください
    - HPのPCでは`F9`を起動時に連打すると開きました
- BIOS/UEFI設定画面を開くことができた場合、「Boot Options」や「Boot Order」といった項目を探し、USBメモリを優先して起動させるデバイスとして設定します
- 設定を保存して再起動すると、PCはUSBメモリからUbuntuのインストーラを起動します

### 2-2. Ubuntuのインストールの開始
- USBメモリからの起動に成功すると、Ubuntuの起動メニューが表示されます
- 通常は`Try or Install Ubuntu`などのオプションを選択します
- 画面の指示に従い、言語選択、キーボードレイアウト、ネットワーク接続などのを設定します
- 最後に、インストールタイプを選択する画面が表示されます
    - 通常「ディスクを削除してUbuntuをインストール」を選択します
    - PC内の既存のデータがすべて削除されるため、事前に必要なデータのバックアップを必ずとっておいてください
    - 慎重に進める場合は、「それ以外の方法」を選択し、パーティションを手動で設定することも可能ですが、初めての方にはオススメしません
- 上記の設定が完了すると、インストールが開始されます
- インストール完了後、指示に従い再起動し、USBメモリを取り外します
- これにより、新しくインストールされたUbuntuが起動します

## 付録:USBの再利用
- Ubuntuのインストールに使用したUSBメモリは、そのままでは他の手段に利用できません。普段使いのストレージとして再利用したり、別のOSのインストールに使用することができるように、USBメモリを元の状態に戻す方法を解説します。

### Appendix-1. USBを差し込み、デバイスの識別子を確認する
- - USBメモリをPCに差し込み、再度`diskutil list`コマンドでデバイス識別子を確認します
```bash
$ diskutil list
```
- サイズなどから識別できると思います。
    - 詳しくは、手順1-1をご確認ください

### Appendix-2. USBメモリのパーティションを削除し、再フォーマットする
- USBメモリの初期化には、既存のパーティションをすべて削除し、新しいファイルシステムでフォーマットします
- 今回は、Macで一般的なファイルシステムである FAT32(MS-DOS FAT)でフォーマットします

```bash
$ diskutil eraseDisk ExFAT USBMEMORY /dev/disk4
```
<details><summary>コマンドの解説</summary>

|コマンド|解説|
|-------|---|
|`eraseDisk`|ディスクを消去し、指定されたファイルシステムでフォーマットするコマンド|
|`ExFAT`|フォーマットするフィイルシステムの指定|
|`USBMEMORY`|USBメモリにつけるボリューム名|
|`/dev/disk4`|デバイス識別子の指定|

</details>

<details><summary>フォーマットの種類について</summary>

| ファイルシステム | 主な特徴 | 対応OS |
|:-:|:-:|:-:|
| FAT32(MS-DOS FAT)  | ほとんどのOSで読み書き可能<br>古いOSやデバイスとの互換性が高いが、4GB以上のファイルを単体で保存できない制限がある  | Windows, macOS, Linux, ほとんどの家電製品  |
| exFAT  |  FAT32の4GBファイルサイズ制限がなく、大容量のファイルを扱うことができる<br>WindowsとmacOSのどちらでも読み書きができるため、異なるOS間でのデータ共有に適している| Windows(XP以降),macOS(OS X 10.6.5以降),Linux(FUSE経由)  |
|  NTFS |  Windowsの標準ファイルシステム<br>アクセス権限や耐障害性に優れルガ、異なるOSでは書き込みができない場合が多い |  Windows(読み書き可),macOS(読み込み可,書き込み別途ドライバ必要),Linux(読み書き別途設定必要) |
|  APFS | Apple File Systemの略でmacOSの標準ファイルシステム<br>SSDに最適化されている  | macOS(High Sierra以降)  |
| ext4  | Linuxの標準ファイルシステム<br>安定性とパフォーマンスに優れるが、WindowsやmacOSでは標準で読み書きできない  | Linux  |

</details>


- 実行後に以下のように出力されると問題なく実行されたことがわかります
```bash
Started erase on disk4
Unmounting disk
Creating the partition map
Waiting for partitions to activate
Formatting disk4s1 as ExFAT with name USBMEMORY
Volume name      : USBMEMORY
Partition offset : 2048 sectors (1048576 bytes)
Volume size      : 1000212480 sectors (512108789760 bytes)
Bytes per sector : 512
Bytes per cluster: 131072
FAT offset       : 2048 sectors (1048576 bytes)
# FAT sectors    : 30720
Number of FATs   : 1
Cluster offset   : 32768 sectors (16777216 bytes)
# Clusters       : 3906952
Volume Serial #  : 6864cae8
Bitmap start     : 2
Bitmap file size : 488369
Upcase start     : 6
Upcase file size : 5836
Root start       : 7
Mounting disk
Finished erase on disk4
```
- このコマンドが完了するとUSBメモリは初期化され、通常のデータ保存用として使えるようになります
- `/Volumes`でも認識されます
```bash
$ ls /Volumes 
Macintosh HD	USBMEMORY
```
- これで、Ubuntu Desktopの作成からUSBメモリの再利用までの一連の作業が完了しました
