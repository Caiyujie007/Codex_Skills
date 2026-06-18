# Resp Network Format Example

本文件只展示步骤一 `Resp.md` 的格式。每段只保留一条记录；不要复制这里的具体节点名、端口名或拓扑关系。

## (a) Switch Resp -> Master Resp

| Record | Transparent path evidence |
|---|---|
| `switch_0_8_resp_main.to_Link_89 -> KN00_1_8_I_I_main.from_Link_89` | `switch_0_8_resp_main.to_Link_89 -> Link_89_main.from_switch_0_8_resp -> Link_89_main.to_KN00_1_8_I_I -> KN00_1_8_I_I_main.from_Link_89` |

## (b) Slave Resp -> Switch Resp

| Record | Transparent path evidence |
|---|---|
| `MEM00_0_8_T_T_main.to_Link_90 -> switch_0_8_resp_main.from_Link_90` | `MEM00_0_8_T_T_main.to_Link_90 -> Link_90_main.from_MEM00_0_8_T_T -> Link_90_main.to_switch_0_8_resp -> switch_0_8_resp_main.from_Link_90` |

## (c) Switch Resp -> Switch Resp

| Record | Transparent path evidence |
|---|---|
| `switch_0_5_resp_main.to_link_0_5_to_0_6_0_resp -> switch_0_6_resp_main.from_link_0_5_to_0_6_0_resp` | `switch_0_5_resp_main.to_link_0_5_to_0_6_0_resp -> link_0_5_to_0_6_0_resp_main.from_switch_0_5_resp -> link_0_5_to_0_6_0_resp_main.to_switch_0_6_resp -> switch_0_6_resp_main.from_link_0_5_to_0_6_0_resp` |

## (d) Switch Resp Internal Reachability

| Record | Case | Internal path evidence |
|---|---|---|
| `switch_0_5_resp_main.from_Link_74 -> switch_0_5_resp_main.to_Link_5` | case0 | `from_Link_74 -> DtpRxBwdFwdPipe_Link_74.Rx -> DtpRxBwdFwdPipe_Link_74.Tx -> Demux_Link_74.Rx -> Demux_Link_74.Tx_0 -> Mux_Link_5.Rx_0 -> Mux_Link_5.Tx -> DtpTxBwdFwdPipe_Link_5.Rx -> DtpTxBwdFwdPipe_Link_5.Tx -> to_Link_5` |
