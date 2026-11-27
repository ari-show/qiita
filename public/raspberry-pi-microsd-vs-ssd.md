---
title: 'Raspberry Pi: microSD vs SSD どれくらい速い？を“数字”で比較してみた'
tags:
  - 電子工作
  - RaspberryPi
  - ssd
  - fio
  - microSD
private: false
updated_at: '2025-11-08T03:40:11+09:00'
id: d4f067301c686d91466f
organization_url_name: null
slide: false
ignorePublish: false
posting_campaign_uuid: null
agreed_posting_campaign_term: false
---
# 1. はじめに
Raspberry Pi の起動ドライブといえば、microSDカードが一般的です。

一方で、SSD を USB または NVMe で接続して起動する運用も広まりつつあります。

**「SSDの方が速いのは分かるけれど、どれくらい速いのか？」**

これは実際に使ってみると気になるポイントです。

本記事では、Raspberry Pi 5 を用いて「microSDカード」と「SATA SSD」の性能を `fio` ベンチマークで定量的に比較しました。
単なる読み書き速度だけでなく、下記の項目も確認し、用途に応じた「どこまでなら microSD で足りるか」を考察します。  

- 連続読み書き（Seq Read/Write）
- ランダム読み込み（Random Read）
- fsync付き書き込み
- 長時間連続書き込み

# 2. 結果サマリ
まずは詳細なグラフやログの前に、各テストでのざっくりした傾向をまとめます。
「とりあえず結論だけ知りたい」人は、この表と最後の考察だけ読んでも大丈夫です。


| テスト                          | 指標                  | microSD                          | SSD (SATA)                         | 備考 |
| ------------------------------ | --------------------- | -------------------------------- | ---------------------------------- | ---- |
| 連続読み書き（Seq Read/Write） | 連続読み書き速度       | 約 23 MiB/s                      | 約 145 MiB/s                       | **SSDが約6倍速い**。OS起動・大きなファイル転送はSSD一択レベル |
| ランダム読み込み（Random Read）| 小さな読み込みの速さ   | 約 3,800 IOPS / 0.26 ms          | 約 5,300 IOPS / 0.19 ms            | **SSDが約1.4〜2倍速い**。細かいファイルが多いほど差が出る |
| fsync付き書き込み              | 確実な書き込みの速さ   | 166 IOPS / 平均 ~4.2 ms          | 178 IOPS / 平均 ~5.2 ms            | IOPSはほぼ同等。**平均はmicroSDやや有利だが、最悪レイテンシはSSDの方が小さい** |
| 長時間連続書き込み             | 2分間の平均書き込み速度| 約 31 MiB/s（総量 ~3.7 GiB）     | 約 198 MiB/s（総量 ~23.2 GiB）     | **SSDが約6倍速く、同じ時間で約6倍書ける**。ただし速度のブレはSSDが大きい |



# 3. 実験環境・条件
## 実験器具
### **Raspberry Pi 5**
- OS: Raspberry Pi OS (64-bit)
    - microSDカードスロット … 一般的な起動ドライブ
    - USB 3.0 ポート … 外付けSSDを接続

### **microSDカード**
- SanDisk Ultra 64GB  

### **SATA SSD**
- KIOXIA SATA3 960GB (SSD-CK960S/N)
- 接続方法: SATA – USB3.2 変換アダプタ経由で Raspberry Pi に接続

## 条件
### OSのキャッシュを無効化
  - fio オプション: `--direct=1`  
  - 意味: OS が一時的にデータをメモリにためることを防ぎ、**ストレージそのものの素の速さ**を測る設定

### テスト時間
  - 各テストを **30〜120秒** 実行
  - 一瞬だけ速い／遅いタイミングに左右されないよう、**ある程度の時間連続して動かして平均的な性能**を確認

### 実験項目
実際の利用シーンをイメージしやすくするために、ストレージの使い方を次の4パターンに分けて計測しました。

|No.|テスト内容                     | どんな場面を想定しているか                       | fioでの指定の例        |
|:-:|:---------------------------|:------------------------|:-----------------------------------------------|
| 1 |連続読み書き（Seq Read/Write） | OS の起動、アプリのインストール、大きなファイル転送 | `bs=1M rw=readwrite`    |
| 2 |ランダム読み込み（Random Read）| 細かいファイルがたくさんあるフォルダの読み込みなど   | `bs=4k rw=randread`     |
| 3 |fsync付き書き込み             | DB の更新、ログ書き込みなど「確実に書き込みたい」処理 | `bs=4k rw=write fsync=1`|
| 4 |長時間連続書き込み            | バックアップ、動画・写真の大量コピーなど            | `bs=1M rw=write`        |


## 用語のざっくり説明
この記事では、次のような指標を使って比較します。

### シーケンシャル性能（Seq）
    大きなファイルを **順番に** 読んだり書いたりしたときの速さです。  
    単位は **MB/s（1秒あたりに何MB読めるか）**。

### ランダム性能（Random / IOPS / レイテンシ）
  たくさんの小さなデータを、あちこち飛びながら読むときの性能です。
  - **IOPS**: 1秒間に何回読み書きできるか  
  - **レイテンシ**: 1回の読み書きにどれくらい時間がかかるか（μs, ms）
  - **P95 / P99 レイテンシ**: 全リクエストのうち、95% / 99% がこの時間以内に終わる、という目安値です。

### fsync（エフシンク）
  「データをちゃんとディスクに書き込むまで待つ」操作です。  
  データベースのコミットや、ログファイルの書き込みなど、**電源が落ちても壊れてほしくないデータ**でよく使われます。

### 持続性能（長時間書き込み）
  最初だけ速くて、すぐ失速するストレージもあります。  
  一定時間書き込みを続けたときに**コピーやバックアップでの安定性**を確認します。
  - 速度がどれくらい落ちるか  
  - 速度のブレがどれくらい大きいか  

# 4. 実験結果

## 4-1. 実験1：連続的な書き込み読み込みテスト
- 実験内容

| 項目             | 説明                                                     |
|:---------------|:--------------------------------------------------------|
| 対象             | 200MBのテストファイル                                       |
| どのように        | 対象ファイルに対して、読み取りと書き込みを同時に実行              |
| どのくらいの単位で | 1MBの大きなブロックサイズで連続的なアクセスを模したテスト         |
| 測定方法          | OSのキャッシュを意図的に無視し、ストレージそのものの「地力」を測定 |

- 結果
連続読み書きでは、SSDはmicroSDの約6倍速く、遅延も数倍小さいため、OS起動や大きなファイルコピーでは体感差が非常に大きいです。

| 項目                   | microSDカード           | SSD (SATA)          | 比較           |
|-----------------------|-----------------------:|--------------------:|:--------------|
| 読み取り速度 (BW)       | 22.7 MiB/s             | 144 MiB/s           | SSDが約6.3倍 高速 |
| 書き込み速度 (BW)       | 23.2 MiB/s             | 147 MiB/s           | SSDが約6.3倍 高速 |
| 読み取り遅延 (avg clat) | 11,133 µs (約 11.1 ms) | 3,685 µs (約 3.7 ms) | SSDが約3倍 応答が速い |
| 書き込み遅延 (avg clat) | 32,142 µs (約 32.1 ms) | 3,164 µs (約 3.2 ms) | SSDが約10倍 応答が速い |
| テスト実行時間          | 4,353 ms (約 4.3 秒)    | 687 ms (約 0.7 秒)   | SSDは約6倍 早く完了 |

<details><summary>microSDカード実験結果</summary>

```bash:実験1 microSDカード
$ fio --name=sdtest --filename=~/fiotest.tmp --size=200M --bs=1M --rw=readwrite --direct=1 --numjobs=1
sdtest: (g=0): rw=rw, bs=(R) 1024KiB-1024KiB, (W) 1024KiB-1024KiB, (T) 1024KiB-1024KiB, ioengine=psync, iodepth=1
fio-3.39
Starting 1 process
sdtest: Laying out IO file (1 file / 200MiB)
Jobs: 1 (f=1): [M(1)][100.0%][r=21.0MiB/s,w=24.0MiB/s][r=21,w=24 IOPS][eta 00m:00s]
sdtest: (groupid=0, jobs=1): err= 0: pid=1642: Wed Nov  5 12:19:01 2025
  read: IOPS=22, BW=22.7MiB/s (23.8MB/s)(99.0MiB/4353msec)
    clat (usec): min=11046, max=16542, avg=11133.29, stdev=550.29
     lat (usec): min=11046, max=16543, avg=11133.49, stdev=550.35
    clat percentiles (usec):
     |  1.00th=[11076],  5.00th=[11076], 10.00th=[11076], 20.00th=[11076],
     | 30.00th=[11076], 40.00th=[11076], 50.00th=[11076], 60.00th=[11076],
     | 70.00th=[11076], 80.00th=[11076], 90.00th=[11076], 95.00th=[11076],
     | 99.00th=[16581], 99.50th=[16581], 99.90th=[16581], 99.95th=[16581],
     | 99.99th=[16581]
   bw (  KiB/s): min=14336, max=26624, per=96.73%, avg=22528.00, stdev=4096.00, samples=8
   iops        : min=   14, max=   26, avg=22.00, stdev= 4.00, samples=8
  write: IOPS=23, BW=23.2MiB/s (24.3MB/s)(101MiB/4353msec); 0 zone resets
    clat (usec): min=26450, max=53286, avg=32142.15, stdev=4158.91
     lat (usec): min=26492, max=53319, avg=32174.05, stdev=4158.11
    clat percentiles (usec):
     |  1.00th=[26608],  5.00th=[29492], 10.00th=[30016], 20.00th=[30278],
     | 30.00th=[30540], 40.00th=[30802], 50.00th=[31065], 60.00th=[31327],
     | 70.00th=[32375], 80.00th=[32900], 90.00th=[33424], 95.00th=[39584],
     | 99.00th=[53216], 99.50th=[53216], 99.90th=[53216], 99.95th=[53216],
     | 99.99th=[53216]
   bw (  KiB/s): min=20480, max=26624, per=100.00%, avg=23808.00, stdev=1876.22, samples=8
   iops        : min=   20, max=   26, avg=23.25, stdev= 1.83, samples=8
  lat (msec)   : 20=49.50%, 50=49.50%, 100=1.00%
  cpu          : usr=0.00%, sys=0.39%, ctx=200, majf=0, minf=7
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=99,101,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=22.7MiB/s (23.8MB/s), 22.7MiB/s-22.7MiB/s (23.8MB/s-23.8MB/s), io=99.0MiB (104MB), run=4353-4353msec
  WRITE: bw=23.2MiB/s (24.3MB/s), 23.2MiB/s-23.2MiB/s (24.3MB/s-24.3MB/s), io=101MiB (106MB), run=4353-4353msec

Disk stats (read/write):
  mmcblk0: ios=97/100, sectors=198656/204800, merge=0/0, ticks=1079/3211, in_queue=4290, util=97.57%
```

</details>
<details><summary>SSD(SATA)実験結果</summary>

```bash:実験1 SSD(SATA)
$ fio --name=sdtest --filename=~/fiotest.tmp --size=200M --bs=1M --rw=readwrite --direct=1 --numjobs=1
sdtest: (g=0): rw=rw, bs=(R) 1024KiB-1024KiB, (W) 1024KiB-1024KiB, (T) 1024KiB-1024KiB, ioengine=psync, iodepth=1
fio-3.39
Starting 1 process
sdtest: Laying out IO file (1 file / 200MiB)

sdtest: (groupid=0, jobs=1): err= 0: pid=1772: Wed Nov  5 14:16:15 2025
  read: IOPS=144, BW=144MiB/s (151MB/s)(99.0MiB/687msec)
    clat (usec): min=2770, max=3998, avg=3684.80, stdev=221.51
     lat (usec): min=2770, max=3999, avg=3684.90, stdev=221.53
    clat percentiles (usec):
     |  1.00th=[ 2769],  5.00th=[ 3392], 10.00th=[ 3490], 20.00th=[ 3589],
     | 30.00th=[ 3687], 40.00th=[ 3720], 50.00th=[ 3720], 60.00th=[ 3785],
     | 70.00th=[ 3818], 80.00th=[ 3818], 90.00th=[ 3851], 95.00th=[ 3851],
     | 99.00th=[ 4015], 99.50th=[ 4015], 99.90th=[ 4015], 99.95th=[ 4015],
     | 99.99th=[ 4015]
   bw (  KiB/s): min=147456, max=147456, per=99.93%, avg=147456.00, stdev= 0.00, samples=1
   iops        : min=  144, max=  144, avg=144.00, stdev= 0.00, samples=1
  write: IOPS=147, BW=147MiB/s (154MB/s)(101MiB/687msec); 0 zone resets
    clat (usec): min=3030, max=8791, avg=3164.00, stdev=579.55
     lat (usec): min=3052, max=8800, avg=3186.24, stdev=578.45
    clat percentiles (usec):
     |  1.00th=[ 3032],  5.00th=[ 3032], 10.00th=[ 3032], 20.00th=[ 3032],
     | 30.00th=[ 3064], 40.00th=[ 3064], 50.00th=[ 3064], 60.00th=[ 3064],
     | 70.00th=[ 3064], 80.00th=[ 3097], 90.00th=[ 3458], 95.00th=[ 3458],
     | 99.00th=[ 3458], 99.50th=[ 8848], 99.90th=[ 8848], 99.95th=[ 8848],
     | 99.99th=[ 8848]
   bw (  KiB/s): min=149504, max=149504, per=99.31%, avg=149504.00, stdev= 0.00, samples=1
   iops        : min=  146, max=  146, avg=146.00, stdev= 0.00, samples=1
  lat (msec)   : 4=99.50%, 10=0.50%
  cpu          : usr=0.29%, sys=2.19%, ctx=200, majf=0, minf=7
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=99,101,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=144MiB/s (151MB/s), 144MiB/s-144MiB/s (151MB/s-151MB/s), io=99.0MiB (104MB), run=687-687msec
  WRITE: bw=147MiB/s (154MB/s), 147MiB/s-147MiB/s (154MB/s-154MB/s), io=101MiB (106MB), run=687-687msec

Disk stats (read/write):
  sda: ios=132/140, sectors=135168/143344, merge=0/0, ticks=401/346, in_queue=747, util=80.85%
```

</details>

## 4-2. 実験2：ランダムアクセス性能（応答速度）の比較

|項目|説明|
|:-|:-|
|対象|1GBのテストファイル|
|どのように|対象ファイル上のランダムな位置から読み取りを実行|
|どのくらいの単位で|4KBの小さなブロックサイズ|
|測定方法|OSキャッシュを無視し、ストレージの**応答速度（レイテンシ）**を測定。特にP95/P99（95/99パーセンタイル値）に着目。|

- 結果
連続読み書き（実験1）では 6倍以上の差がありましたが、4KB ランダム読み込みでは IOPS・レイテンシともに おおよそ 1.4倍〜2倍程度 の差に収まっています。
それでも、P95〜P99.9 のレイテンシを見ると、「レアケースでの待たされ具合」がSSDの方がかなり小さいことがわかります。

| 項目                     | microSDカード        | SSD (SATA)            | 比較 |
|:------------------------|---------------------:|----------------------:|:---------------------------------------|
| IOPS（1秒あたりの処理回数）| 3,786 IOPS           | 5,275 IOPS            | SSDが約1.4倍 高性能 |
| 転送速度 (BW)            | 14.8 MiB/s           | 20.6 MiB/s            | SSDが約1.4倍 高速 |
| 平均レイテンシ（avg clat）| 263.03 µs（約 0.26 ms）| 188.53 µs（約 0.19 ms）| SSDが約1.4倍 レイテンシが短い |
| 95% レイテンシ           | 375 µs                | 192 µs                        | SSDが約2倍（1.95倍） レイテンシが短い |
| 99% レイテンシ           | 379 µs                | 196 µs                        | SSDが約1.9倍 レイテンシが短い |
| 99.9% レイテンシ         | 383 µs                | 198 µs                        | SSDが約1.9倍 レイテンシが短い |


<details><summary>microSDカード実験結果</summary>

```bash:実験2 microSDカード
$ fio --name=latp --filename=~/latp.tmp --size=1G --bs=4k --rw=randread \
    --iodepth=1 --direct=1 --time_based=1 --runtime=30 \
    --lat_percentiles=1 --percentile_list=95:99:99.9
latp: (g=0): rw=randread, bs=(R) 4096B-4096B, (W) 4096B-4096B, (T) 4096B-4096B, ioengine=psync, iodepth=1
fio-3.39
Starting 1 process
latp: Laying out IO file (1 file / 1024MiB)
Jobs: 1 (f=1): [r(1)][100.0%][r=14.8MiB/s][r=3791 IOPS][eta 00m:00s]
latp: (groupid=0, jobs=1): err= 0: pid=1661: Wed Nov  5 12:24:03 2025
  read: IOPS=3786, BW=14.8MiB/s (15.5MB/s)(444MiB/30001msec)
    clat (usec): min=195, max=23177, avg=263.03, stdev=78.23
     lat (usec): min=195, max=23177, avg=263.16, stdev=78.24
    clat percentiles (usec):
     | 95.0th=[  375], 99.0th=[  379], 99.9th=[  383]
    lat percentiles (usec):
     | 95.0th=[  375], 99.0th=[  379], 99.9th=[  383]
   bw (  KiB/s): min=14456, max=15264, per=100.00%, avg=15149.29, stdev=107.85, samples=59
   iops        : min= 3614, max= 3816, avg=3787.32, stdev=26.96, samples=59
  lat (usec)   : 250=31.66%, 500=68.34%, 750=0.01%
  lat (msec)   : 2=0.01%, 10=0.01%, 50=0.01%
  cpu          : usr=0.57%, sys=4.42%, ctx=113659, majf=0, minf=8
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=113595,0,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=14.8MiB/s (15.5MB/s), 14.8MiB/s-14.8MiB/s (15.5MB/s-15.5MB/s), io=444MiB (465MB), run=30001-30001msec

Disk stats (read/write):
  mmcblk0: ios=113242/14, sectors=905936/184, merge=0/9, ticks=29112/106, in_queue=29218, util=96.92%

```

</details>
<details><summary>SSD(SATA)実験結果</summary>

```bash:実験2 SSD(SATA)
$ fio --name=latp --filename=~/latp.tmp --size=1G --bs=4k --rw=randread \ 
    --iodepth=1 --direct=1 --time_based=1 --runtime=30 \
    --lat_percentiles=1 --percentile_list=95:99:99.9
latp: (g=0): rw=randread, bs=(R) 4096B-4096B, (W) 4096B-4096B, (T) 4096B-4096B, ioengine=psync, iodepth=1
fio-3.39
Starting 1 process
latp: Laying out IO file (1 file / 1024MiB)
Jobs: 1 (f=1): [r(1)][100.0%][r=20.6MiB/s][r=5273 IOPS][eta 00m:00s]
latp: (groupid=0, jobs=1): err= 0: pid=1788: Wed Nov  5 14:20:37 2025
  read: IOPS=5275, BW=20.6MiB/s (21.6MB/s)(618MiB/30001msec)
    clat (usec): min=142, max=6065, avg=188.53, stdev=83.38
     lat (usec): min=142, max=6065, avg=188.65, stdev=83.38
    clat percentiles (usec):
     | 95.0th=[  192], 99.0th=[  196], 99.9th=[  198]
    lat percentiles (usec):
     | 95.0th=[  192], 99.0th=[  196], 99.9th=[  198]
   bw (  KiB/s): min=20720, max=21920, per=100.00%, avg=21104.00, stdev=208.46, samples=60
   iops        : min= 5180, max= 5480, avg=5276.00, stdev=52.11, samples=60
  lat (usec)   : 250=99.97%, 500=0.01%
  lat (msec)   : 2=0.01%, 4=0.01%, 10=0.02%
  cpu          : usr=0.71%, sys=9.93%, ctx=158301, majf=0, minf=8
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=158280,0,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=20.6MiB/s (21.6MB/s), 20.6MiB/s-20.6MiB/s (21.6MB/s-21.6MB/s), io=618MiB (648MB), run=30001-30001msec

Disk stats (read/write):
  sda: ios=157844/136, sectors=1262752/130664, merge=0/5, ticks=29078/502, in_queue=29596, util=96.08%
```

</details>

## 4-3. 実験3：fsync（4KB write）  

|項目|説明|
|:-|:-|
|対象|256MBのテストファイル|
|どのように|4KBのデータを書き込み、1回ごとにディスクへの確実な保存を強制|
|どのくらいの単位で|4KBの小さなブロックサイズ|
|測定方法|OSキャッシュを無視。データベースのコミットなど、**データの信頼性（永続性）**が求められる処理の性能を測定。|

- 結果
fsync の評価は、「平均的にどれくらいか」よりも「最悪でもどれくらいで返ってくるか」 の方が効いてくることが多いです。今回は平均はmicroSDがやや有利ですが、P99〜P99.9を見るとSSDの方が「ハマり」が小さい結果でした。
そのため、「fsyncだけを見ればmicroSDでも致命的な差は出ない」が、他のI/Oパターンや容量・耐久性を考えると、トータルではSSDを選んだ方が無難かもしれません。

| 項目                         | microSDカード          | SSD (SATA)                       | 比較                                       |
|-----------------------------|----------------------:|-----------------------:|------|
| IOPS（1秒あたりの処理回数）     | 166 IOPS              | 178 IOPS              | SSDが約1.1倍（ほぼ同等）|
| 転送速度 (BW)                 | 664 KiB/s             | 715 KiB/s             | SSDが約1.1倍（ほぼ同等）|
| fsync 平均レイテンシ（avg sync）| 4,152 µs（約 4.15 ms） | 5,232 µs（約 5.23 ms） | **平均値だけ見ると microSD が約1.3倍速い** |
| fsync 99% レイテンシ   　      | 7,570 µs（約 7.57 ms） | 5,735 µs（約 5.74 ms） | SSDの方が約1.3倍 レイテンシが小さい|
| fsync 99.9% レイテンシ         | 28,967 µs（約 28.9 ms）| 11,076 µs（約 11.0 ms）| SSDの方が約2.6倍 レイテンシが小さい|



<details><summary>microSDカード実験結果</summary>

```bash:実験3 microSDカード
$ fio --name=fsync --filename=~/fsync.tmp --size=256M --bs=4k --rw=write \
    --direct=1 --iodepth=1 --fsync=1 --runtime=30 --time_based=1
fsync: (g=0): rw=write, bs=(R) 4096B-4096B, (W) 4096B-4096B, (T) 4096B-4096B, ioengine=psync, iodepth=1
fio-3.39
Starting 1 process
fsync: Laying out IO file (1 file / 256MiB)
Jobs: 1 (f=1): [W(1)][100.0%][w=616KiB/s][w=154 IOPS][eta 00m:00s]
fsync: (groupid=0, jobs=1): err= 0: pid=1686: Wed Nov  5 12:26:48 2025
  write: IOPS=166, BW=664KiB/s (680kB/s)(19.5MiB/30003msec); 0 zone resets
    clat (usec): min=809, max=22931, avg=1866.03, stdev=780.41
     lat (usec): min=809, max=22932, avg=1866.25, stdev=780.41
    clat percentiles (usec):
     |  1.00th=[  988],  5.00th=[ 1045], 10.00th=[ 1205], 20.00th=[ 1319],
     | 30.00th=[ 1500], 40.00th=[ 1598], 50.00th=[ 1745], 60.00th=[ 1860],
     | 70.00th=[ 1926], 80.00th=[ 2057], 90.00th=[ 2704], 95.00th=[ 3523],
     | 99.00th=[ 4293], 99.50th=[ 4359], 99.90th=[ 5932], 99.95th=[ 9634],
     | 99.99th=[22938]
   bw (  KiB/s): min=  576, max=  784, per=99.95%, avg=664.40, stdev=46.96, samples=60
   iops        : min=  144, max=  196, avg=166.10, stdev=11.74, samples=60
  lat (usec)   : 1000=1.00%
  lat (msec)   : 2=70.22%, 4=25.15%, 10=3.59%, 20=0.02%, 50=0.02%
  fsync/fdatasync/sync_file_range:
    sync (usec): min=2065, max=38652, avg=4152.80, stdev=1646.21
    sync percentiles (usec):
     |  1.00th=[ 2507],  5.00th=[ 2638], 10.00th=[ 2900], 20.00th=[ 2966],
     | 30.00th=[ 3195], 40.00th=[ 3589], 50.00th=[ 3720], 60.00th=[ 4146],
     | 70.00th=[ 4817], 80.00th=[ 5145], 90.00th=[ 5538], 95.00th=[ 6521],
     | 99.00th=[ 7570], 99.50th=[ 8848], 99.90th=[28967], 99.95th=[31065],
     | 99.99th=[38536]
  cpu          : usr=0.07%, sys=0.57%, ctx=9991, majf=0, minf=6
  IO depths    : 1=200.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,4983,0,4983 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=1

Run status group 0 (all jobs):
  WRITE: bw=664KiB/s (680kB/s), 664KiB/s-664KiB/s (680kB/s-680kB/s), io=19.5MiB (20.4MB), run=30003-30003msec

Disk stats (read/write):
  mmcblk0: ios=0/14928, sectors=0/278528, merge=0/19888, ticks=0/29663, in_queue=29663, util=98.61%

```

</details>
<details><summary>SSD(SATA)実験結果</summary>

```bash:実験3 SSD(SATA)
$ fio --name=fsync --filename=~/fsync.tmp --size=256M --bs=4k --rw=write \
    --direct=1 --iodepth=1 --fsync=1 --runtime=30 --time_based=1
fsync: (g=0): rw=write, bs=(R) 4096B-4096B, (W) 4096B-4096B, (T) 4096B-4096B, ioengine=psync, iodepth=1
fio-3.39
Starting 1 process
fsync: Laying out IO file (1 file / 256MiB)
Jobs: 1 (f=1): [W(1)][100.0%][w=716KiB/s][w=179 IOPS][eta 00m:00s]
fsync: (groupid=0, jobs=1): err= 0: pid=1799: Wed Nov  5 14:22:01 2025
  write: IOPS=178, BW=715KiB/s (732kB/s)(20.9MiB/30003msec); 0 zone resets
    clat (usec): min=244, max=6222, avg=359.28, stdev=234.61
     lat (usec): min=245, max=6222, avg=359.55, stdev=234.61
    clat percentiles (usec):
     |  1.00th=[  310],  5.00th=[  314], 10.00th=[  318], 20.00th=[  318],
     | 30.00th=[  322], 40.00th=[  326], 50.00th=[  330], 60.00th=[  330],
     | 70.00th=[  338], 80.00th=[  412], 90.00th=[  424], 95.00th=[  433],
     | 99.00th=[  445], 99.50th=[  498], 99.90th=[ 6128], 99.95th=[ 6128],
     | 99.99th=[ 6194]
   bw (  KiB/s): min=  696, max=  744, per=100.00%, avg=715.07, stdev=11.70, samples=60
   iops        : min=  174, max=  186, avg=178.77, stdev= 2.92, samples=60
  lat (usec)   : 250=0.02%, 500=99.50%, 750=0.30%
  lat (msec)   : 4=0.04%, 10=0.15%
  fsync/fdatasync/sync_file_range:
    sync (usec): min=4556, max=11711, avg=5232.38, stdev=434.69
    sync percentiles (usec):
     |  1.00th=[ 4686],  5.00th=[ 4817], 10.00th=[ 4883], 20.00th=[ 5014],
     | 30.00th=[ 5145], 40.00th=[ 5145], 50.00th=[ 5211], 60.00th=[ 5276],
     | 70.00th=[ 5342], 80.00th=[ 5407], 90.00th=[ 5473], 95.00th=[ 5538],
     | 99.00th=[ 5735], 99.50th=[ 7963], 99.90th=[11076], 99.95th=[11207],
     | 99.99th=[11731]
  cpu          : usr=0.03%, sys=0.95%, ctx=10726, majf=0, minf=6
  IO depths    : 1=200.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,5363,0,5363 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=1

Run status group 0 (all jobs):
  WRITE: bw=715KiB/s (732kB/s), 715KiB/s-715KiB/s (732kB/s-732kB/s), io=20.9MiB (22.0MB), run=30003-30003msec

Disk stats (read/write):
  sda: ios=0/16169, sectors=0/430200, merge=0/21413, ticks=0/30176, in_queue=55151, util=98.11%
```

</details>

## 4-4. 実験4：長時間 Write

|項目|説明|
|:-|:-|
|対象|3GBのテストファイル|
|どのように|対象ファイルに連続的に書き込みを実行|
|どのくらいの単位で|1MBの大きなブロックサイズ|
|測定方法|OSキャッシュを無視 (--direct=1)し、120秒間（2分間） (--runtime=120) の持続的な書き込み性能を測定。|

- 結果
長時間の連続書き込みでは、平均的な書き込み速度・総書き込み量ともに SSD が microSD の約6倍以上 という結果でした。
一方で、microSD は常に 30 MiB/s 前後で推移するのに対し、SSD は内部キャッシュやガーベジコレクション、温度制御の影響で、瞬間的には 6 MiB/s まで落ち込む区間もあります。
つまり、「とにかく速くたくさん書きたいならSSD」「遅くてもいいから挙動が素直で読めるほうがいいならmicroSD」 という性格の違いが見えてきます。

| 項目                       | microSDカード                         | SSD (SATA)                          | 比較                                      |
|----------------------------|--------------------------------------:|-------------------------------------:|-------------------------------------------|
| 平均 IOPS                  | 31 IOPS                               | 197 IOPS                             | SSDが約6.35倍 高性能                      |
| 平均転送速度 (BW)          | 31.3 MiB/s                            | 198 MiB/s                            | SSDが約6.3倍 高速                         |
| 2分間の総書き込み量        | 約 3.7 GiB （3756 MiB）               | 約 23.2 GiB                          | SSDが約6.3倍 多く書き込めた               |
| 転送速度の範囲 (Min–Max)   | 28.0 MiB/s 〜 36.0 MiB/s              | 6.0 MiB/s 〜 324 MiB/s               | microSDはほぼ一定, SSDは大きく揺れる      |
| 転送速度の標準偏差 (stdev) | 約 1.2 MiB/s                          | 約 112.8 MiB/s                       | SSD側の速度変動が桁違いに大きい           |
| 速度の安定性               | 非常に安定（ほぼ30 MiB/s前後で推移） | 速度のブレが大きい（内部処理の影響） | 平均はSSD圧勝だが、ばらつきはmicroSDが小さい |



<details><summary>microSDカード実験結果</summary>

```bash:実験4microSDカード
$ fio --name=sustain --filename=~/sustain.tmp --size=3G --bs=1M \
    --rw=write --direct=1 --time_based=1 --runtime=120 --iodepth=2
sustain: (g=0): rw=write, bs=(R) 1024KiB-1024KiB, (W) 1024KiB-1024KiB, (T) 1024KiB-1024KiB, ioengine=psync, iodepth=2
fio-3.39
Starting 1 process
sustain: Laying out IO file (1 file / 3072MiB)
note: both iodepth >= 1 and synchronous I/O engine are selected, queue depth will be capped at 1
Jobs: 1 (f=1): [W(1)][100.0%][w=32.0MiB/s][w=32 IOPS][eta 00m:00s]
sustain: (groupid=0, jobs=1): err= 0: pid=1699: Wed Nov  5 12:29:41 2025
  write: IOPS=31, BW=31.3MiB/s (32.8MB/s)(3756MiB/120018msec); 0 zone resets
    clat (usec): min=23696, max=65467, avg=31930.48, stdev=4706.67
     lat (usec): min=23715, max=65486, avg=31952.04, stdev=4706.71
    clat percentiles (usec):
     |  1.00th=[25035],  5.00th=[26346], 10.00th=[28967], 20.00th=[30016],
     | 30.00th=[30278], 40.00th=[30540], 50.00th=[31065], 60.00th=[31589],
     | 70.00th=[31851], 80.00th=[32900], 90.00th=[34341], 95.00th=[42730],
     | 99.00th=[47973], 99.50th=[60031], 99.90th=[63701], 99.95th=[64226],
     | 99.99th=[65274]
   bw (  KiB/s): min=28672, max=36864, per=100.00%, avg=32048.20, stdev=1248.70, samples=239
   iops        : min=   28, max=   36, avg=31.30, stdev= 1.22, samples=239
  lat (msec)   : 50=99.07%, 100=0.93%
  cpu          : usr=0.07%, sys=0.25%, ctx=3846, majf=0, minf=6
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,3756,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=2

Run status group 0 (all jobs):
  WRITE: bw=31.3MiB/s (32.8MB/s), 31.3MiB/s-31.3MiB/s (32.8MB/s-32.8MB/s), io=3756MiB (3938MB), run=120018-120018msec

Disk stats (read/write):
  mmcblk0: ios=0/3809, sectors=0/7685344, merge=0/99, ticks=0/120037, in_queue=120038, util=99.75%
```

</details>
<details><summary>SSD(SATA)実験結果</summary>

```bash:実験4 SSD(SATA)
$ fio --name=sustain --filename=~/sustain.tmp --size=3G --bs=1M \
    --rw=write --direct=1 --time_based=1 --runtime=120 --iodepth=2
sustain: (g=0): rw=write, bs=(R) 1024KiB-1024KiB, (W) 1024KiB-1024KiB, (T) 1024KiB-1024KiB, ioengine=psync, iodepth=2
fio-3.39
Starting 1 process
sustain: Laying out IO file (1 file / 3072MiB)
note: both iodepth >= 1 and synchronous I/O engine are selected, queue depth will be capped at 1
Jobs: 1 (f=1): [W(1)][100.0%][w=123MiB/s][w=123 IOPS][eta 00m:00s]
sustain: (groupid=0, jobs=1): err= 0: pid=1810: Wed Nov  5 14:27:38 2025
  write: IOPS=197, BW=198MiB/s (207MB/s)(23.2GiB/120241msec); 0 zone resets
    clat (msec): min=3, max=623, avg= 5.04, stdev=25.86
     lat (msec): min=3, max=623, avg= 5.06, stdev=25.86
    clat percentiles (msec):
     |  1.00th=[    4],  5.00th=[    4], 10.00th=[    4], 20.00th=[    4],
     | 30.00th=[    4], 40.00th=[    4], 50.00th=[    4], 60.00th=[    4],
     | 70.00th=[    4], 80.00th=[    4], 90.00th=[    4], 95.00th=[    4],
     | 99.00th=[    7], 99.50th=[  309], 99.90th=[  321], 99.95th=[  502],
     | 99.99th=[  625]
   bw (  KiB/s): min= 6144, max=331776, per=100.00%, avg=204498.82, stdev=115503.55, samples=238
   iops        : min=    6, max=  324, avg=199.71, stdev=112.80, samples=238
  lat (msec)   : 4=97.73%, 10=1.31%, 20=0.26%, 50=0.16%, 100=0.01%
  lat (msec)   : 250=0.01%, 500=0.48%, 750=0.05%
  cpu          : usr=0.42%, sys=2.22%, ctx=23848, majf=0, minf=6
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,23766,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=2

Run status group 0 (all jobs):
  WRITE: bw=198MiB/s (207MB/s), 198MiB/s-198MiB/s (207MB/s-207MB/s), io=23.2GiB (24.9GB), run=120241-120241msec

Disk stats (read/write):
  sda: ios=0/47595, sectors=0/48672936, merge=0/85, ticks=0/179284, in_queue=181252, util=99.05%
```

</details>

## 4-4. 実験結果サマリ (再掲)

| テスト                          | 指標                  | microSD                          | SSD (SATA)                         | 備考 |
| ------------------------------ | --------------------- | -------------------------------- | ---------------------------------- | ---- |
| 連続読み書き（Seq Read/Write） | 連続読み書き速度       | 約 23 MiB/s                      | 約 145 MiB/s                       | **SSDが約6倍速い**。OS起動・大きなファイル転送はSSD一択レベル |
| ランダム読み込み（Random Read）| 小さな読み込みの速さ   | 約 3,800 IOPS / 0.26 ms          | 約 5,300 IOPS / 0.19 ms            | **SSDが約1.4〜2倍速い**。細かいファイルが多いほど差が出る |
| fsync付き書き込み              | 確実な書き込みの速さ   | 166 IOPS / 平均 ~4.2 ms          | 178 IOPS / 平均 ~5.2 ms            | IOPSはほぼ同等。**平均はmicroSDやや有利だが、最悪レイテンシはSSDの方が小さい** |
| 長時間連続書き込み             | 2分間の平均書き込み速度| 約 31 MiB/s（総量 ~3.7 GiB）     | 約 198 MiB/s（総量 ~23.2 GiB）     | **SSDが約6倍速く、同じ時間で約6倍書ける**。ただし速度のブレはSSDが大きい |

# 5. 用途別おすすめ

ここまでの結果をふまえて、「どんな用途なら microSD で足りて、どこから SSD を使いたくなるか」をざっくり整理します。

## 5-1. OS起動・パッケージ管理

- 該当しそうな使い方
  - Raspberry Pi OS の起動
  - `apt upgrade` などのパッケージ更新
  - デスクトップ環境でのアプリ起動・終了 など

- 実験結果
  - 実験1（連続読み書き）で **約6倍の差**
  - ランダム読み込みも SSD が 1.4〜2倍 有利

- 結論
  - **とりあえず動けばOK / サーバ用途でコンソール中心 -> microSDでも可**
    - 使えないほど遅くはいかないと
    - OSインストールなど少し時間はかかるかも
  - **快適さ重視 -> SSD推奨**
    - ブート時間、パッケージ更新、アプリ起動などが目に見えてスムーズに動く
  
## 5-2. DB / ログ用途

- 該当しそうな使い方
  - SQLite / PostgreSQL などの軽量DB
  - アプリケーションログの永続化
  - センサー値を一定周期で追記するようなログ

- 実験結果
  - 実験2（ランダムRead）：SSD が 1.4〜2倍 有利
  - 実験3（fsync）：  
    - IOPS・平均レイテンシは **ほぼ同等〜microSDやや有利**
    - ただし **P99〜P99.9 の最悪レイテンシは SSD の方が小さい**

- 結論
  - **ライトなDB / ログ -> microSD**
    - 小規模な SQLite、テキストログ程度なら、fsync 性能だけ見れば致命的な差は出ないかと
  - **更新頻度が高いDB / 複数サービスを同時に書く -> SSD推奨**
    - ランダムI/O全体では SSD が有利で、  
      「たまにすごく遅くなる」ケースも SSD の方が抑えられる
    - 24時間稼働するサービスや、DBをがっつり触る用途では SSD を選んだ方が安全

## 5-3. Docker / Webサービス

- 該当しそうな使い方
  - Docker でコンテナを大量に立ち上げる
  - Docker イメージ・レイヤのダウンロード・展開
  - Nginx / API サーバ / バッチ処理などの Web 系サービス

- 実験結果
  - イメージの展開 -> 実験1のような **連続読み書き**
  - コンテナ内のファイルアクセス -> 実験2のような **ランダムI/O**
  - ログやDBを併用することも多い

- 結論
  - **ここは基本的に SSD 一択に近い**
    - イメージ展開・ログ書き込み・細かいファイルアクセスが混ざるため、実験1・2・4 の「SSD有利な場面」が現れる
    - 開発用途でコンテナを頻繁に作り直すなら、**microSDだとかなりストレスに感じるかも**

## 5-4. NAS / 写真保管

- 該当しそうな使い方
  - 自宅用の簡易NAS
  - 写真・動画の保管（Immich など）
  - 大きなメディアファイルを LAN 経由で読み書き

- 観点
  - 大きなファイルの読み書き → 実験1・4 の **連続I/Oが支配的**
  - 長時間書き込みでは、SSD が **約6倍のスループット**

- 結論
  - **NAS / 写真・動画の保管は SSD推奨**
    - バックアップや大量コピーで待ち時間が大きく変わる
    - 容量面でも、数十 GB の microSD より SSD の方が現実的
  - 「ちょっとしたファイル置き場」でトラフィックも少なければ、microSDでも動きますが、**体感速度と容量を考えると SSD を選んだ方が後悔は少ない**かと

## 5-5. センサー用途・小規模スクリプト

- 該当しそうな使い方
  - GPIO やシリアル、I2C センサーの値を取得して記録
  - 定期的にAPIを叩いて結果をログに追記
  - cron で回る軽いスクリプト など

- 観点
  - I/O量がそもそも多くない
  - 多くの場合、ボトルネックは **ネットワークや外部サービスの応答時間**

- 結論
  - **このクラスの用途なら microSDで十分**
    - ログの書き込み頻度がそこまで高くなければ、実験2〜4の差はほとんど差は少ない
  - ただし、  
    - ログをがっつり溜める  
    - 後から解析したい  
    といった用途なら、**容量と耐久性の面でSSDを検討する価値**はある

# 6. まとめ
本記事では、Raspberry Pi 5 上で microSDカード と SATA SSD を接続し、`fio` を用いて両者の速度差を定量的に確認しました。

「どこまでなら microSD で足りて、どこから SSD にすると快適か？」という観点で、
連続読み書き・ランダムアクセス・fsync・長時間書き込みを分けて見ることで、用途ごとの向き・不向きが少し見えてきたと思います。

Raspberry Pi で何かを作るときに、microSD で始めるか、最初から SSD に投資するかを考える際のひとつの判断材料になればうれしいです。
