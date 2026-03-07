import 'package:flutter/material.dart';

class SecureModeToggle extends StatefulWidget {
  const SecureModeToggle({Key? key}) : super(key: key);

  @override
  State<SecureModeToggle> createState() => _SecureModeToogleState();
}

class _SecureModeToogleState extends State<SecureModeToggle> {
  bool _isSecureModeEnabled = false;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Discreet Emergency Mode',
              style: TextStyle(fontSize: 14),
            ),
            Switch(
              value: _isSecureModeEnabled,
              onChanged: (value) {
                setState(() => _isSecureModeEnabled = value);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      value ? '🔒 Secure Mode Activated' : '🔓 Secure Mode Deactivated',
                    ),
                  ),
                );
              },
              activeColor: const Color(0xFFE91E63),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          _isSecureModeEnabled
              ? '✓ Emergency features can be triggered discreetly'
              : 'Enable for discreet emergency activation',
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }
}
