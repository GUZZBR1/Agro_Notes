<?php

declare(strict_types=1);

namespace Drupal\farm_field\Plugin\Field\FieldFormatter;

use Drupal\Core\Field\Attribute\FieldFormatter;
use Drupal\Core\Field\FieldItemListInterface;
use Drupal\Core\Field\FormatterBase;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\Core\Url;

/**
 * Plugin implementation of the 'url_link' formatter.
 */
#[FieldFormatter(
  id: 'url_link',
  label: new TranslatableMarkup('Link to URL'),
  field_types: ['uri'],
)]
class UrlLinkFormatter extends FormatterBase {

  /**
   * {@inheritdoc}
   */
  public function viewElements(FieldItemListInterface $items, $langcode) {
    /** @var \Drupal\Core\Field\FieldItemList $items */
    $elements = [];

    // This is a clone of Drupal core's UriLinkFormatter, but it only renders
    // a link if the URI is a valid URL.
    /** @var \Drupal\Core\Field\Plugin\Field\FieldType\UriItem $item */
    foreach ($items->getIterator() as $delta => $item) {
      if (!$item->isEmpty()) {
        if (filter_var($item->value, FILTER_VALIDATE_URL)) {
          $element = [
            '#type' => 'link',
            '#url' => Url::fromUri($item->value),
            '#title' => $item->value,
          ];
        }
        else {
          $element = [
            '#type' => 'markup',
            '#markup' => $item->value,
          ];
        }
        $elements[$delta] = $element;
      }
    }

    return $elements;
  }

}
