<?php

declare(strict_types=1);

namespace Drupal\farm_entity\Hook;

use Drupal\Core\Entity\ContentEntityFormInterface;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Form hook implementations for farm_entity.
 */
class FormHooks {

  /**
   * Implements hook_form_alter().
   *
   * Hides the revision control from the user.
   *
   * @see EntityHooks::entityPresave()
   */
  #[Hook('form_alter')]
  public function formAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Only alter content entity forms.
    $form_object = $form_state->getFormObject();
    if (!$form_object instanceof ContentEntityFormInterface) {
      return;
    }

    // Only apply to farm controlled entities.
    $entity = $form_object->getEntity();
    $entity_types = [
      'asset',
      'log',
      'organization',
      'plan',
      'quantity',
    ];
    if (!in_array($entity->getEntityTypeId(), $entity_types)) {
      return;
    }

    // Disable access to the revision checkbox.
    $form['revision']['#access'] = FALSE;
  }

}
