# Description

The protocol consists of 4 command/answer requests.
The communication initiator is always the PC (this program), while the
embedded device answers to the requested command or acknoledges the
requested command.

Here are examples of the 4 commands, the data is being transmitted in
big endian binary format, we represent it here in using hex strings.

Hex strings starting with "> " are the commands (PC -> Device) and
the ones starting with "< " are the answers (Device -> PC).

## Ping/Pong

```
> CD000000
< DC000000
```

## Send the total count of the RFIDs before sending the RFIDs in chunks

```
> CD01006E
< DC01006E
```

## Send the RFIDs by chunks of 50 IDs (50 is 32 in hex)

* Note: We split the list to chunks because the device has limited memory, so it can not buffer more than 255 bytes of information before processing it.

### Chunk 1

```
> CD020032
> 00000000
> 00000001
> 00000002
> ...
> 00000031
< DC020032
```

### Chunk 2

```
> CD020032
> 01000000
> 01000001
> 01000002
> ...
> 01000031
< DC020032
```

### Chunk 3

```
> CD02000A
> 02000000
> 02000001
> 02000002
...
> 02000009
< DC02000A
```

## Read the last connected RFID from the Device

```
> CD030000
< DC030000
< 12345678
```
