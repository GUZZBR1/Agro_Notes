<?php

declare(strict_types=1);

namespace Drupal\organization\Form;

use Drupal\Core\Entity\EntityForm;
use Drupal\Core\Form\FormStateInterface;

/**
 * Form controller for organization type entities.
 *
 * @package Drupal\organization\Form
 */
class OrganizationTypeForm extends EntityForm {

  /**
   * The organization type entity.
   *
   * @var \Drupal\organization\Entity\OrganizationTypeInterface
   */
  protected $entity;

  /**
   * {@inheritdoc}
   */
  public function form(array $form, FormStateInterface $form_state) {
    $form = parent::form($form, $form_state);
    $organization_type = $this->entity;

    $form['label'] = [
      '#type' => 'textfield',
      '#title' => $this->t('Label'),
      '#maxlength' => 255,
      '#default_value' => $organization_type->label(),
      '#description' => $this->t('Label for the organization type.'),
      '#required' => TRUE,
    ];

    $form['id'] = [
      '#type' => 'machine_name',
      '#default_value' => $organization_type->id(),
      '#machine_name' => [
        'exists' => '\Drupal\organization\Entity\OrganizationType::load',
      ],
      '#disabled' => !$organization_type->isNew(),
    ];

    $form['description'] = [
      '#type' => 'textarea',
      '#title' => $this->t('Description'),
      '#default_value' => $organization_type->getDescription(),
    ];

    $form['new_revision'] = [
      '#type' => 'checkbox',
      '#title' => $this->t('Create new revision'),
      '#default_value' => $organization_type->shouldCreateNewRevision(),
    ];

    return $form;
  }

  /**
   * {@inheritdoc}
   */
  public function save(array $form, FormStateInterface $form_state) {
    $organization_type = $this->entity;
    $status = $organization_type->save();

    switch ($status) {
      case SAVED_NEW:
        $this->messenger()->addMessage($this->t('Created the %label organization type.', [
          '%label' => $organization_type->label(),
        ]));
        break;

      default:
        $this->messenger()->addMessage($this->t('Saved the %label organization type.', [
          '%label' => $organization_type->label(),
        ]));
    }
    $form_state->setRedirectUrl($organization_type->toUrl('collection'));

    return $status;
  }

}
