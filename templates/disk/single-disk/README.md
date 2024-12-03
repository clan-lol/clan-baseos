---
description = "Simple single disk schema"
---
# Description

This schema defines a GPT-based disk layout.

### **Disk Overview**

- **Name**: `main-{{uuid}}`
- **Device**: `{{mainDisk}}`

### **Partitions**

1. **EFI System Partition (ESP)**
   - Size: `500M`.
   - Filesystem: `vfat`.
   - Mount Point: `/boot` (secure `umask=0077`).

2. **Root Partition**
   - Size: Remaining disk space (`100%`).
   - Filesystem: `ext4`.
   - Mount Point: `/`.
