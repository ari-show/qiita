---
title: 【Ubuntu】カーネル更新で `nvidia-smi` がエラーになった時の復旧手順（RTX 5060 Ti）
tags:
  - Ubuntu
  - nvidia-smi
private: false
updated_at: '2026-08-03T21:51:25+09:00'
id: db70c1a0d6c54c11b7b2
organization_url_name: null
slide: false
ignorePublish: false
posting_campaign_uuid: null
agreed_posting_campaign_term: false
---
## 背景
ある日、いつも通りGPUの確認をするため、 `nvidia-smi` を叩いたところ、以下のようなエラーが発生してGPUが認識されなくなりました。

```bash
$ nvidia-smi
NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver.
Make sure that the latest NVIDIA driver is installed and running.
```

本環境は Ubuntu、GPUは **RTX 5060 Ti**
今回は、OSのカーネルアップデートによってNVIDIAドライバとの紐付けが切れてしまった状態からの復旧手順を書きました

## エラーの原因調査

まずはモジュールが読み込まれているか手動でロードを試みます

```bash
$ sudo modprobe nvidia
modprobe : FATAL: Module nvidia not found in directory /lib/modules/7.0.0.28-generic
```

現在動いているカーネル（`7.0.0.28-generic`）用のモジュールが見つからないと怒られます
カーネルヘッダーが不足しているのかと思いインストールを試みましたが、こちらは既に最新版が入っていました

```bash
$ sudo apt install linux-headers-$(uname -r)
linux-headers-7.0.0-28-generic is already the newest version (7.0.0-28.28).

```

次に `dkms` のステータスを確認しようとしたところ、**そもそも `dkms` コマンドがインストールされていない**ことが判明しました

```bash
$ dkms status
Command 'dkms' not found, but can be installed with:
sudo apt install dkms

```

通常、カーネルがアップデートされた際は DKMS がよしなにドライバを再構築してくれます
しかし、今回の環境では DKMS が入っていなかったため、カーネル更新のタイミングでドライバが置き去りになり、通信できなくなってしまったようです

## 解決手順：ubuntu-driversで推奨ドライバを再インストール

手動で DKMS を構成するよりも、Ubuntu標準の `ubuntu-drivers` コマンドを使ってシステムに最適なドライバをクリーンインストールするのが手っ取り早く確実です

### 1. 推奨ドライバの確認

以下のコマンドで、現在のシステムとGPU（RTX 5060 Ti）に適合するドライバのリストを確認

```bash
$ ubuntu-drivers devices
== /sys/devices/pci0000:00/0000:00:03.1/0000:0b:00.0 ==
modalias : pci:v000010DEd00002D04sv000010B0sd0000F331bc03sc00i00
vendor   : NVIDIA Corporation
model    : GB206 [GeForce RTX 5060 Ti]
driver   : nvidia-driver-580 - distro non-free
driver   : nvidia-driver-610 - distro non-free
driver   : nvidia-driver-595-server - distro non-free
driver   : nvidia-driver-595-open - distro non-free recommended
# ...（省略）...

```

出力結果の右端に `recommended` と記載されているバージョンを探します
今回は **`nvidia-driver-595-open`** がシステムから推奨されていました

:::note info
PyTorchなどでCUDAをガッツリ使う場合、末尾に `-open` がつかないプロプライエタリ版（`nvidia-driver-595` や `610`）を選ぶことも多いですが、最近はオープンソースモジュール版（`-open`）でも概ね問題なく動作します。今回は素直に推奨されたものを入れました
:::


### 2. ドライバのインストール

確認したパッケージ名を指定して `apt` でインストールします

:::note warn
`sudo ubuntu-drivers autoinstall` は最近の環境ではコマンド仕様が変わっておりエラーになることも
:::

```bash
$ sudo apt update
$ sudo apt install nvidia-driver-595-open
```

### 3. 再起動と動作確認

インストールが完了したら、新しいドライバをカーネルに読み込ませるため、システムを再起動します

```bash
$ sudo reboot
```

再起動後、改めて `nvidia-smi` を実行し、無事にGPUのステータス表が表示されれば復旧完了

## まとめ

* カーネル更新後に `nvidia-smi` が動かなくなったら、DKMSの不在やビルド失敗を疑う
* `ubuntu-drivers devices` で `recommended` なドライバを確認する
* `apt install nvidia-driver-XXX` で再インストールして再起動する
