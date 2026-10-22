<?php

declare(strict_types=1);

namespace Drupal\farm_log_quantity\Hook;

use Drupal\Core\Entity\EntityFormInterface;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\farm_log_quantity\FarmLogQuantityHelper;

/**
 * Form hook implementations for farm_log_quantity.
 */
class FormHooks {

  /**
   * Implements hook_form_BASE_FORM_ID_alter().
   */
  #[Hook('form_log_form_alter')]
  public function formLogFormAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Alter the Quantity inline entity form to set the default quantity type.
    if (!empty($form['quantity']['widget']['actions']['bundle']['#options'])) {
      $bundle_select = &$form['quantity']['widget']['actions']['bundle'];

      // Load the log type storage.
      assert($form_state->getFormObject() instanceof EntityFormInterface);
      /** @var \Drupal\log\Entity\Log $entity */
      $entity = $form_state->getFormObject()->getEntity();

      // Determine the default quantity type.
      $default_type = FarmLogQuantityHelper::defaultQuantityType($entity->bundle());

      // Set the default value.
      if (array_key_exists($default_type, $bundle_select['#options'])) {
        $bundle_select['#default_value'] = $default_type;
      }
    }
  }

}
