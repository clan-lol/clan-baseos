---
description = "A secure, file synchronization app for devices over networks, offering a private alternative to cloud services."
---
## Usage

We recommend configuring this module as an sync-service through the provided options. Although it provides a Web GUI through which more usage scenarios are supported.

## Features

- **Private and Secure**: Syncthing uses TLS encryption to secure data transfer between devices, ensuring that only the intended devices can read your data.
- **Decentralized**: No central server is involved in the data transfer. Each device communicates directly with others.
- **Open Source**: The source code is openly available for audit and contribution, fostering trust and continuous improvement.
- **Cross-Platform**: Syncthing supports multiple platforms including Windows, macOS, Linux, BSD, and Android.
- **Real-time Synchronization**: Changes made to files are synchronized in real-time across all connected devices.
- **Web GUI**: It includes a user-friendly web interface for managing devices and configurations. (`127.0.0.1:8384`)

## Configuration

- **Share Folders**: Select folders to share with connected devices and configure permissions and synchronization parameters.

!!! info
    Clan automatically discovers other devices. Automatic discovery requires one machine to be an [introducer](#clansyncthingintroducer)

    If that is not the case you can add the other device by its Device ID manually.
    You can find and share Device IDs under the "Add Device" button in the Web GUI. (`127.0.0.1:8384`)

## Troubleshooting

- **Sync Conflicts**: Resolve synchronization conflicts manually by reviewing file versions and modification times in the Web GUI (`127.0.0.1:8384`).

## Support

- **Documentation**: Extensive documentation is available on the [Syncthing website](https://docs.syncthing.net/).
