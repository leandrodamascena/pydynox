//! Field encryption module for DynamoDB attributes.
//!
//! Provides per-field encryption using AWS KMS. This allows encrypting
//! sensitive data like SSN or credit cards at the field level, not just
//! table-level encryption.

use crate::errors::{map_kms_error, EncryptionError};
use aws_config::BehaviorVersion;
use aws_sdk_kms::primitives::Blob;
use aws_sdk_kms::Client as KmsClient;
use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use pyo3::prelude::*;
use std::collections::HashMap;
use tokio::runtime::Runtime;

/// Prefix for encrypted values to detect them on read.
const ENCRYPTED_PREFIX: &str = "ENC:";

/// KMS encryptor for field-level encryption.
///
/// Wraps AWS KMS client to encrypt/decrypt individual field values.
/// Mode control (ReadWrite/WriteOnly/ReadOnly) is handled in Python.
#[pyclass]
pub struct KmsEncryptor {
    client: KmsClient,
    key_id: String,
    context: HashMap<String, String>,
}

#[pymethods]
impl KmsEncryptor {
    /// Create a new KMS encryptor.
    ///
    /// Args:
    ///     key_id: KMS key ID, ARN, or alias.
    ///     region: AWS region (optional, uses default if not set).
    ///     context: Encryption context for additional security (optional).
    #[new]
    #[pyo3(signature = (key_id, region=None, context=None))]
    pub fn new(
        key_id: String,
        region: Option<String>,
        context: Option<HashMap<String, String>>,
    ) -> PyResult<Self> {
        let rt = Runtime::new()
            .map_err(|e| EncryptionError::new_err(format!("Failed to create runtime: {}", e)))?;

        let client = rt.block_on(async {
            let mut config_loader = aws_config::defaults(BehaviorVersion::latest());
            if let Some(r) = region {
                config_loader = config_loader.region(aws_config::Region::new(r));
            }
            let config = config_loader.load().await;
            KmsClient::new(&config)
        });

        Ok(Self {
            client,
            key_id,
            context: context.unwrap_or_default(),
        })
    }

    /// Encrypt a plaintext string.
    ///
    /// Args:
    ///     plaintext: String to encrypt.
    ///
    /// Returns:
    ///     Base64-encoded ciphertext with "ENC:" prefix.
    ///
    /// Raises:
    ///     EncryptionError: If encryption fails.
    pub fn encrypt(&self, plaintext: &str) -> PyResult<String> {
        let rt = Runtime::new()
            .map_err(|e| EncryptionError::new_err(format!("Failed to create runtime: {}", e)))?;

        let ciphertext = rt.block_on(async {
            let mut req = self
                .client
                .encrypt()
                .key_id(&self.key_id)
                .plaintext(Blob::new(plaintext.as_bytes()));

            for (k, v) in &self.context {
                req = req.encryption_context(k, v);
            }

            req.send().await
        });

        match ciphertext {
            Ok(output) => {
                let blob = output
                    .ciphertext_blob()
                    .ok_or_else(|| EncryptionError::new_err("No ciphertext returned from KMS"))?;
                let encoded = BASE64.encode(blob.as_ref());
                Ok(format!("{}{}", ENCRYPTED_PREFIX, encoded))
            }
            Err(e) => Err(map_kms_error(e)),
        }
    }

    /// Decrypt a ciphertext string.
    ///
    /// Args:
    ///     ciphertext: Base64-encoded ciphertext with "ENC:" prefix.
    ///
    /// Returns:
    ///     Original plaintext string.
    ///
    /// Raises:
    ///     EncryptionError: If decryption fails.
    ///     ValueError: If ciphertext format is invalid.
    pub fn decrypt(&self, ciphertext: &str) -> PyResult<String> {
        // Check for prefix
        let encoded = match ciphertext.strip_prefix(ENCRYPTED_PREFIX) {
            Some(s) => s,
            None => {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "Ciphertext must start with 'ENC:' prefix",
                ));
            }
        };

        // Decode base64
        let decoded = BASE64.decode(encoded).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Invalid base64: {}", e))
        })?;

        let rt = Runtime::new()
            .map_err(|e| EncryptionError::new_err(format!("Failed to create runtime: {}", e)))?;

        let plaintext = rt.block_on(async {
            let mut req = self.client.decrypt().ciphertext_blob(Blob::new(decoded));

            for (k, v) in &self.context {
                req = req.encryption_context(k, v);
            }

            req.send().await
        });

        match plaintext {
            Ok(output) => {
                let blob = output
                    .plaintext()
                    .ok_or_else(|| EncryptionError::new_err("No plaintext returned from KMS"))?;
                String::from_utf8(blob.as_ref().to_vec()).map_err(|e| {
                    pyo3::exceptions::PyValueError::new_err(format!("Invalid UTF-8: {}", e))
                })
            }
            Err(e) => Err(map_kms_error(e)),
        }
    }

    /// Check if a value is encrypted.
    ///
    /// Args:
    ///     value: String to check.
    ///
    /// Returns:
    ///     True if value has encryption prefix.
    #[staticmethod]
    pub fn is_encrypted(value: &str) -> bool {
        value.starts_with(ENCRYPTED_PREFIX)
    }

    /// Get the KMS key ID.
    #[getter]
    pub fn key_id(&self) -> &str {
        &self.key_id
    }
}

/// Register encryption classes in the Python module.
pub fn register_encryption(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<KmsEncryptor>()?;
    Ok(())
}
