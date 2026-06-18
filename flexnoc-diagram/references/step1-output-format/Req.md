# Req Network Format Example

本文件只展示步骤一 `Req.md` 的格式。每段只保留一条记录；不要复制这里的具体节点名、端口名或拓扑关系。

## (a) Master Req -> Switch Req

| Record | Transparent path evidence |
|---|---|
| `KN00_1_8_I_I_main.to_Link_88 -> switch_0_8_req_main.from_Link_88` | `KN00_1_8_I_I_main.to_Link_88 -> Link_88_main.from_KN00_1_8_I_I -> Link_88_main.to_switch_0_8_req -> switch_0_8_req_main.from_Link_88` |

## (b) Switch Req -> Slave Req

| Record | Transparent path evidence |
|---|---|
| `switch_0_8_req_main.to_Link_91 -> MEM00_0_8_T_T_main.from_Link_91` | `switch_0_8_req_main.to_Link_91 -> Link_91_main.from_switch_0_8_req -> Link_91_main.to_MEM00_0_8_T_T -> MEM00_0_8_T_T_main.from_Link_91` |

## (c) Switch Req -> Switch Req

| Record | Transparent path evidence |
|---|---|
| `switch_0_5_req_main.to_link_0_5_to_0_6_0_req -> switch_0_6_req_main.from_link_0_5_to_0_6_0_req` | `switch_0_5_req_main.to_link_0_5_to_0_6_0_req -> link_0_5_to_0_6_0_req_main.from_switch_0_5_req -> link_0_5_to_0_6_0_req_main.to_switch_0_6_req -> switch_0_6_req_main.from_link_0_5_to_0_6_0_req` |

## (d) Switch Req Internal Reachability

| Record | Case | Internal path evidence |
|---|---|---|
| `switch_0_5_req_main.from_Link_24 -> switch_0_5_req_main.to_Link_75` | case0 | `from_Link_24 -> DtpRxBwdFwdPipe_Link_24.Rx -> DtpRxBwdFwdPipe_Link_24.Tx -> Demux_Link_24.Rx -> Demux_Link_24.Tx_0 -> Mux_Link_75.Rx_0 -> Mux_Link_75.Tx -> DtpTxBwdFwdPipe_Link_75.Rx -> DtpTxBwdFwdPipe_Link_75.Tx -> to_Link_75` |
