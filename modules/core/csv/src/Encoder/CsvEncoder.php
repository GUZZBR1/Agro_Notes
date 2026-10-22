<?php

declare(strict_types=1);

namespace Drupal\farm_csv\Encoder;

use Drupal\csv_serialization\Encoder\CsvEncoder as ContribCsvEncoder;

/**
 * Adds CSV encoder support for the Serialization API.
 */
class CsvEncoder extends ContribCsvEncoder {

  public function __construct(
    $delimiter = ",",
    $enclosure = '"',
    $escape_char = "\\",
    $strip_tags = TRUE,
    $trim_values = TRUE,
    protected bool $sanitize = TRUE,
  ) {
    parent::__construct($delimiter, $enclosure, $escape_char, $strip_tags, $trim_values);
  }

  /**
   * {@inheritdoc}
   */
  protected function formatValue($value) {
    $value = parent::formatValue($value);

    // Sanitize against CSV injection vectors by prefixing cells that start with
    // suspicious characters (=, -, +, or @) with a tab.
    // @see https://georgemauer.net/2017/10/07/csv-injection.html
    if ($this->sanitize) {
      if (preg_match('/^[=@\-+]/', $value)) {
        $value = "\t" . $value;
      }
    }

    return $value;
  }

  /**
   * {@inheritdoc}
   */
  public function setSettings(array $settings) {
    parent::setSettings($settings);
    $this->sanitize = $settings['sanitize'] ?? $this->sanitize;
  }

}
