<?php

declare(strict_types=1);

namespace Drupal\farm_id_tag\Plugin\Field\FieldFormatter;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Field\Attribute\FieldFormatter;
use Drupal\Core\Field\FieldDefinitionInterface;
use Drupal\Core\Field\FieldItemListInterface;
use Drupal\Core\Field\FormatterBase;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Plugin implementation of the 'id tag' formatter.
 */
#[FieldFormatter(
  id: 'id_tag',
  label: new TranslatableMarkup('ID tag'),
  field_types: ['id_tag'],
)]
class IdTagFormatter extends FormatterBase {

  public function __construct(
    $plugin_id,
    $plugin_definition,
    FieldDefinitionInterface $field_definition,
    array $settings,
    $label,
    $view_mode,
    array $third_party_settings,
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {
    parent::__construct($plugin_id, $plugin_definition, $field_definition, $settings, $label, $view_mode, $third_party_settings);
  }

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition) {
    // @todo Use autowiring and remove this when the parent class does.
    // @see https://www.drupal.org/project/drupal/issues/3552110
    return new static(
      $plugin_id,
      $plugin_definition,
      $configuration['field_definition'],
      $configuration['settings'],
      $configuration['label'],
      $configuration['view_mode'],
      $configuration['third_party_settings'],
      $container->get('entity_type.manager'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function viewElements(FieldItemListInterface $items, $langcode) {
    $elements = [];

    foreach ($items as $delta => $item) {

      // Render the ID if it exists.
      if (!empty($item->id)) {
        $elements[$delta]['id'] = [
          '#markup' => $this->t('ID: @value', ['@value' => $item->id]),
        ];
      }

      // Render the type if it exists. Use the tag_type label.
      $tag_type_storage = $this->entityTypeManager->getStorage('tag_type');
      if (!empty($item->type) && $tag_type = $tag_type_storage->load($item->type)) {
        $elements[$delta]['type'] = [
          '#markup' => $this->t('Type: @value', ['@value' => $tag_type->label()]),
        ];
      }

      // Render the location if it exists.
      if (!empty($item->location)) {
        $elements[$delta]['location'] = [
          '#markup' => $this->t('Location: @value', ['@value' => $item->location]),
        ];
      }
    }

    $elements['#attached']['library'][] = 'farm_id_tag/id_tag_field';
    // PHPStan throws the following error on the next line:
    // Method
    // Drupal\farm_id_tag\Plugin\Field\FieldFormatter\IdTagFormatter::viewElements()
    // should return array<int, array<int|string, mixed>> but returns
    // array<int|string, array<string, array<int|string,
    // Drupal\Core\StringTranslation\TranslatableMarkup|string>>>.
    // We ignore this because we are following Drupal core's pattern.
    // @phpstan-ignore return.type
    return $elements;
  }

}
